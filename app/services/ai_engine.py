"""
Core AI engine for generating activity plans.
Builds context-aware prompts and parses structured responses.
"""

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass
from datetime import date

from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from app.config import settings
from app.prompts import (
    AGE_PROFILES,
    ENCOURAGEMENT_EXAMPLES,
    GENERATE_INSTRUCTIONS,
    LANGUAGE_HINTS,
    TRANSLATE_INSTRUCTIONS,
)
from app.services.safety_validator import validate_activity

logger = logging.getLogger(__name__)
_client: AsyncOpenAI | None = None
# Limit concurrent OpenAI calls per worker process to avoid rate-limit bursts.
_ai_semaphore = asyncio.Semaphore(5)
_RATE_LIMIT_MAX_RETRIES = 5

ACTIVITY_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "activity_plan",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "activities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "desc": {"type": "string"},
                            "instr": {"type": "array", "items": {"type": "string"}},
                            "age_min": {"type": "integer"},
                            "age_max": {"type": "integer"},
                            "dur": {"type": "integer"},
                            "energy": {"type": "string", "enum": ["calm", "moderate", "active"]},
                            "cat": {"type": "string", "enum": ["creative", "science", "sport", "cooking", "outdoor", "social", "sensory", "music", "logic"]},
                            "weather": {"type": "string", "enum": ["any", "indoor", "outdoor"]},
                            "mat": {"type": "array", "items": {"type": "string"}},
                            "goals": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": [
                            "title",
                            "desc",
                            "instr",
                            "age_min",
                            "age_max",
                            "dur",
                            "energy",
                            "cat",
                            "weather",
                            "mat",
                            "goals",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["activities"],
            "additionalProperties": False,
        },
    },
}


@dataclass
class GenerateContentConfig:
    system_instruction: str
    temperature: float = 0.4
    max_tokens: int = 2000
    timeout: float = 55.0
    response_format: dict | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=0)
    return _client


class ActivityGenerationError(Exception):
    def __init__(self, user_message: str, internal_reason: str):
        super().__init__(internal_reason)
        self.user_message = user_message
        self.internal_reason = internal_reason


LOCATION_HINTS = {
    "home": "Generate home-friendly indoor activities only. Avoid noisy or space-heavy formats.",
    "cafe": (
        "Generate calm, low-mess, compact-table activities suitable for cafes/public places. "
        "Avoid running, loud movement, water, and messy materials."
    ),
    "outdoor": "Generate outdoor activities and adapt exactly to the current weather conditions.",
}
LOCATION_CUSTOM = (
    "This is a custom location. Adapt activity setup, safety, noise level, and required space "
    "to this exact place while keeping activities practical."
)

MODE_HINTS = {
    "evening": "It's a school evening - activities should be relaxing, not too energetic, 20-45 min each.",
    "vacation": "It's vacation/holidays - can include longer projects, outdoor adventures, cooking, etc.",
    "weekend": "It's a weekend - mix of active and creative activities, can be longer.",
}


def _age_categories(children_info: list[dict]) -> list[str]:
    sorted_children = sorted(children_info, key=lambda c: c["age_months"])
    seen = set()
    result = []
    for c in sorted_children:
        cat = c["age_category"]
        if cat not in seen:
            seen.add(cat)
            result.append(cat)
    return result


def _resolve_language(language: str | None) -> str:
    if language and language.lower().startswith("uk"):
        return "uk"
    return "en"


def _build_system_instruction(language: str) -> str:
    encouragement = ENCOURAGEMENT_EXAMPLES.get(language, ENCOURAGEMENT_EXAMPLES.get("en", ""))
    return f"{GENERATE_INSTRUCTIONS}\n\n{encouragement}"


def _build_dynamic_instructions(categories: list[str], language: str) -> str:
    lang_name = "Ukrainian" if language == "uk" else "English"

    age_sections = []
    for cat in categories:
        profile = AGE_PROFILES.get(cat, "")
        if profile:
            age_sections.append(f"## {cat.upper()}\n{profile}")
    age_block = "\n\n".join(age_sections) if age_sections else AGE_PROFILES.get("toddler", "")

    lang_hints = LANGUAGE_HINTS.get(language, "")
    return "\n".join(filter(None, [
        f"Write ALL text fields in {lang_name} only.",
        f"\nAGE PROFILES:\n{age_block}",
        f"\nLANGUAGE STYLE:\n{lang_hints}" if lang_hints else "",
    ]))


def _build_generation_prompt(
    children_info: list[dict],
    num_activities: int,
    available_time: int,
    weather: dict | None,
    materials: list[str],
    energy_level: str | None,
    theme: str | None,
    favorite_titles: list[str],
    mix_favorites: bool,
    excluded_titles: list[str],
    mode: str,
    language: str,
    location: str | None = None,
) -> str:
    categories = _age_categories(children_info)
    parts = [
        _build_dynamic_instructions(categories, language),
        f"Generate exactly {num_activities} unique activities.\n",
    ]
    categories_set: set[str] = set(categories)

    if len(children_info) == 1:
        child = children_info[0]
        parts.append(f"Child: {child['age_months']} months old ({child['age_category']} category)")
    else:
        ages_sorted = sorted(children_info, key=lambda c: c["age_months"])
        youngest = ages_sorted[0]
        oldest = ages_sorted[-1]
        age_gap = oldest["age_months"] - youngest["age_months"]
        n_joint = max(2, round(num_activities * 0.65))

        parts.append(f"\n=== PLAN FOR {len(children_info)} CHILDREN ===")
        for c in ages_sorted:
            parts.append(f"  • {c['age_months']} months ({c['age_category']})")
        parts.append(f"Age spread: {youngest['age_months']}–{oldest['age_months']} months (gap: {age_gap} months)")

        parts.append(
            f"\nGenerate AT LEAST {n_joint} out of {num_activities} activities as JOINT activities "
            f"where ALL children participate at the same time with age-appropriate roles."
        )
        parts.append(
            "The remaining activities may target a specific age group, "
            "but still mention how the other child(ren) can observe or do a simpler variant."
        )

        parts.append("\nFor EVERY joint activity — mandatory requirements:")
        parts.append(
            f"  1. YOUNGER child ({youngest['age_months']}mo, {youngest['age_category']}): "
            f"simpler sub-task, helper role, parallel play version, mimics the older child."
        )
        parts.append(
            f"  2. OLDER child ({oldest['age_months']}mo, {oldest['age_category']}): "
            f"leads the activity, explains to younger, tackles the harder version, sets up materials."
        )
        parts.append(
            "  3. No child is ever idle — every step must have an active role for each child."
        )
        parts.append(
            "  4. In 'instr': at least 2 steps must explicitly name both age roles "
            "(e.g., 'The older child draws the outline while the younger child fills in with finger paints.')."
        )
        parts.append(
            "  5. In 'desc': start by explaining how this activity works for children of different ages "
            "and why the age gap is an advantage here, not a barrier."
        )
        parts.append(
            "  6. Scale materials: larger/softer pieces for the younger child, "
            "finer/more detailed tools for the older child."
        )

        if age_gap >= 36:
            parts.append(
                f"\nLARGE AGE GAP ({age_gap} months — major developmental difference):"
            )
            parts.append(
                "  - Older child acts as a mini-teacher: explains rules, demonstrates, checks the younger child's work. "
                "This builds empathy and leadership in the older child."
            )
            parts.append(
                "  - Younger child benefits from social modeling: watching and imitating the older child "
                "accelerates their learning far beyond what solo play achieves."
            )
            parts.append(
                "  - Choose activities where complexity scales naturally by design "
                "(painting: older child creates detailed scene, younger child fills background; "
                "building: older child architects, younger child places large blocks; "
                "cooking: older child measures/reads recipe, younger child pours/stirs)."
            )
            parts.append(
                "  - AVOID activities that require similar fine motor precision — "
                "the younger child will be frustrated and the older child bored."
            )
        elif age_gap >= 18:
            parts.append(
                f"\nMODERATE AGE GAP ({age_gap} months):"
            )
            parts.append(
                "  - Older child can guide and explain. Both can attempt most steps "
                "with slight difficulty variation."
            )
            parts.append(
                "  - Good for cooperative projects with clear sub-tasks assigned by ability."
            )
        else:
            parts.append(
                f"\nSMALL AGE GAP ({age_gap} months):"
            )
            parts.append(
                "  - Children can work as near-equals. Focus on side-by-side cooperation "
                "and gentle friendly competition."
            )

        parts.append("=== END MULTI-CHILD ===\n")

    if weather:
        parts.append(f"\nWeather: {weather['description']}, {weather['temperature']}°C")
        if not weather["is_outdoor_ok"]:
            parts.append("Weather is NOT suitable for outdoor activities. Generate INDOOR activities only.")

    parts.append(f"Mode: {mode}")
    if location:
        parts.append(f"Preferred location: {location}")
        parts.append(LOCATION_HINTS.get(location, LOCATION_CUSTOM))

    hint = MODE_HINTS.get(mode)
    if hint:
        parts.append(hint)

    if energy_level:
        parts.append(f"Preferred energy level: {energy_level}")

    if materials:
        parts.append(f"\nAvailable materials at home: {', '.join(materials)}")
        parts.append("PRIORITIZE activities using these materials.")

    if theme:
        parts.append(f"\nRequested theme: {theme}")
        parts.append("ALL activities should relate to this theme.")

    if mix_favorites and favorite_titles:
        parts.append(f"\nUser's favorite activity types (generate SIMILAR but NEW): {', '.join(favorite_titles[:3])}")

    if excluded_titles:
        parts.append(f"\nDO NOT repeat these activities (already suggested): {', '.join(excluded_titles[:10])}")

    return "\n".join(parts)


def _ensure_str(value) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value) if value else ""


def _normalize_activity_keys(act: dict, language: str) -> dict:
    key_map = {
        "title": "title",
        "desc": "description",
        "instr": "instructions",
        "t_uk": "title_uk",
        "t_en": "title_en",
        "d_uk": "description_uk",
        "d_en": "description_en",
        "i_uk": "instructions_uk",
        "i_en": "instructions_en",
        "age_min": "min_age_months",
        "age_max": "max_age_months",
        "dur": "duration_minutes",
        "energy": "energy_level",
        "cat": "category",
        "weather": "weather_type",
        "mat": "materials_needed",
        "goals": "developmental_goals",
    }
    normalized: dict = {}
    for k, v in act.items():
        normalized[key_map.get(k, k)] = v

    title = (
        normalized.pop("title", None)
        or normalized.get("title_uk")
        or normalized.get("title_en")
        or ""
    )
    description = (
        normalized.pop("description", None)
        or normalized.get("description_uk")
        or normalized.get("description_en")
        or ""
    )
    instructions = (
        normalized.pop("instructions", None)
        or normalized.get("instructions_uk")
        or normalized.get("instructions_en")
        or ""
    )

    title = _ensure_str(title)
    description = _ensure_str(description)
    instructions = _ensure_str(instructions)

    if language == "uk":
        normalized["title_uk"] = title
        normalized["description_uk"] = description
        normalized["instructions_uk"] = instructions
        normalized["title_en"] = title
        normalized["description_en"] = description
        normalized["instructions_en"] = instructions
    else:
        normalized["title_en"] = title
        normalized["description_en"] = description
        normalized["instructions_en"] = instructions
        normalized["title_uk"] = title
        normalized["description_uk"] = description
        normalized["instructions_uk"] = instructions

    for list_field in ("materials_needed", "developmental_goals"):
        val = normalized.get(list_field)
        if val is None:
            normalized[list_field] = []
        elif isinstance(val, str):
            normalized[list_field] = [s.strip() for s in val.split(",") if s.strip()]

    for int_field in ("min_age_months", "max_age_months", "duration_minutes"):
        val = normalized.get(int_field)
        if val is not None:
            if isinstance(val, str):
                match = re.search(r"\d+", val)
                normalized[int_field] = int(match.group()) if match else 0
            else:
                try:
                    normalized[int_field] = int(val)
                except (ValueError, TypeError):
                    normalized[int_field] = 0

    return normalized


async def generate_activities(
    children_info: list[dict],
    num_activities: int = 4,
    available_time: int = 120,
    weather: dict | None = None,
    materials: list[str] | None = None,
    energy_level: str | None = None,
    theme: str | None = None,
    favorite_titles: list[str] | None = None,
    mix_favorites: bool = False,
    excluded_titles: list[str] | None = None,
    mode: str = "daily",
    location: str | None = None,
    language: str | None = None,
) -> list[dict]:
    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY is missing in backend environment")
        raise ActivityGenerationError(
            "AI service is not configured on the server. Please try again later.",
            "Missing OPENAI_API_KEY",
        )

    lang = _resolve_language(language)

    logger.info(
        "Generating activities via OpenAI model=%s num=%s mode=%s children=%s lang=%s",
        settings.openai_model,
        num_activities,
        mode,
        len(children_info),
        lang,
    )

    client = _get_openai_client()

    user_prompt = _build_generation_prompt(
        children_info=children_info,
        num_activities=num_activities,
        available_time=available_time,
        weather=weather,
        materials=materials or [],
        energy_level=energy_level,
        theme=theme,
        favorite_titles=favorite_titles or [],
        mix_favorites=mix_favorites,
        excluded_titles=excluded_titles or [],
        mode=mode,
        location=location,
        language=lang,
    )

    content_config = GenerateContentConfig(
        system_instruction=_build_system_instruction(lang),
        temperature=0.4,
        max_tokens=4500,
        response_format=ACTIVITY_RESPONSE_SCHEMA,
        timeout=55.0,
    )
    call_kwargs = dict(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": content_config.system_instruction},
            {"role": "user", "content": user_prompt},
        ],
        response_format=content_config.response_format,
        temperature=content_config.temperature,
        max_tokens=content_config.max_tokens,
        timeout=content_config.timeout,
    )

    response = None
    for attempt in range(_RATE_LIMIT_MAX_RETRIES + 1):
        try:
            async with _ai_semaphore:
                response = await client.chat.completions.create(**call_kwargs)
            break
        except RateLimitError as exc:
            if attempt >= _RATE_LIMIT_MAX_RETRIES:
                logger.warning("OpenAI rate limit exceeded after %d retries", attempt)
                raise ActivityGenerationError(
                    "AI service is busy right now. Please retry in a minute.",
                    f"OpenAI rate limit: {exc}",
                ) from exc
            delay = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                "OpenAI rate limited, retrying in %.1fs (attempt %d/%d)",
                delay, attempt + 1, _RATE_LIMIT_MAX_RETRIES,
            )
            await asyncio.sleep(delay)
        except AuthenticationError as exc:
            logger.exception("OpenAI authentication failed")
            raise ActivityGenerationError(
                "AI request failed: invalid API key configuration.",
                f"OpenAI auth error: {exc}",
            ) from exc
        except APIConnectionError as exc:
            logger.exception("OpenAI connection failure")
            raise ActivityGenerationError(
                "Could not connect to AI service. Please check internet and retry.",
                f"OpenAI connection error: {exc}",
            ) from exc
        except (APIStatusError, BadRequestError) as exc:
            logger.exception("OpenAI API error")
            raise ActivityGenerationError(
                "AI service returned an error. Please try again later.",
                f"OpenAI error: {exc}",
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected OpenAI generation error")
            raise ActivityGenerationError(
                "Unexpected AI generation error. Please try again.",
                f"Unexpected generation exception: {exc}",
            ) from exc

    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.exception("AI response is not valid JSON")
        raise ActivityGenerationError(
            "AI response format was invalid. Please retry.",
            f"JSON parse error: {exc}; content={content!r}",
        ) from exc

    if isinstance(parsed, dict):
        activities = parsed.get("activities", [])
    else:
        activities = parsed

    if not isinstance(activities, list):
        logger.error("AI payload does not contain activities list")
        raise ActivityGenerationError(
            "AI response did not contain activity list. Please retry.",
            f"Invalid payload type: {type(activities).__name__}",
        )

    min_age = min(c["age_months"] for c in children_info)
    validated = []
    rejected_count = 0

    for raw in activities:
        act = _normalize_activity_keys(raw, lang)
        is_safe, issues = validate_activity(act, min_age)
        if is_safe:
            validated.append(act)
        else:
            rejected_count += 1
            logger.warning("Rejected unsafe activity: issues=%s title=%s", issues, act.get("title_en"))

    logger.info(
        "Generated activities total=%s validated=%s rejected=%s",
        len(activities),
        len(validated),
        rejected_count,
    )

    if not validated:
        logger.warning("All generated activities failed safety validation")
        return []

    return validated


async def translate_activities(
    activities: list[dict],
    source_language: str,
    target_language: str,
) -> list[dict]:
    """Translate title, description, and instructions to the target language."""
    if not activities or not settings.openai_api_key:
        return []

    source = _resolve_language(source_language)
    target = _resolve_language(target_language)
    if source == target:
        return []

    src_title = "title_uk" if source == "uk" else "title_en"
    src_desc = "description_uk" if source == "uk" else "description_en"
    src_instr = "instructions_uk" if source == "uk" else "instructions_en"

    payload = [
        {
            "id": idx,
            "title": act.get(src_title, ""),
            "description": act.get(src_desc, ""),
            "instructions": act.get(src_instr, ""),
        }
        for idx, act in enumerate(activities)
    ]

    source_name = "Ukrainian" if source == "uk" else "English"
    target_name = "Ukrainian" if target == "uk" else "English"

    client = _get_openai_client()
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": f"{TRANSLATE_INSTRUCTIONS}\nTranslate from {source_name} to {target_name}.",
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2000,
            timeout=30.0,
        )
    except Exception as exc:
        logger.exception("Activity translation failed: %s", exc)
        return []

    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.exception("Translation response is not valid JSON")
        return []

    items = parsed.get("items", parsed) if isinstance(parsed, dict) else parsed
    if not isinstance(items, list):
        return []

    by_id = {item.get("id"): item for item in items if isinstance(item, dict)}
    results = []
    for idx, _act in enumerate(activities):
        item = by_id.get(idx, {})
        results.append({
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "instructions": item.get("instructions", ""),
        })
    return results


def determine_mode(child_age_months: int, is_vacation: bool, day_of_week: int) -> str:
    """Determine activity mode based on age, vacation status, and day of week.
    day_of_week: 0=Monday, 6=Sunday
    """
    if child_age_months < 72:  # under 6 -- always daily mode
        return "daily"

    if is_vacation:
        return "vacation"

    if day_of_week >= 5:  # Saturday or Sunday
        return "weekend"

    return "evening"


def get_num_activities(mode: str) -> int:
    return {
        "daily": 3,
        "evening": 2,
        "weekend": 3,
        "vacation": 4,
    }.get(mode, 3)
