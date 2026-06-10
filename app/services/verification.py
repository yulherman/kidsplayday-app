"""
Verification engine that scores activities on how interesting/engaging they are.
Uses AI self-check + community signals.
"""

import json

from openai import AsyncOpenAI

from app.config import settings
from app.prompts import VERIFY_INSTRUCTIONS

_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client

VERIFY_PROMPT_TEMPLATE = """Activity: {title}
Description: {description}
Target age: {age_range}
Duration: {duration} minutes
Materials: {materials}
"""


async def ai_verify_activity(activity_data: dict) -> float:
    if not settings.openai_api_key:
        return 0.7  # default score when no API key

    client = _get_openai_client()

    user_prompt = VERIFY_PROMPT_TEMPLATE.format(
        title=activity_data.get("title_en", ""),
        description=activity_data.get("description_en", ""),
        age_range=f"{activity_data.get('min_age_months', 0)}-{activity_data.get('max_age_months', 144)} months",
        duration=activity_data.get("duration_minutes", 30),
        materials=", ".join(activity_data.get("materials_needed", [])),
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": VERIFY_INSTRUCTIONS},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=300,
        )

        scores = json.loads(response.choices[0].message.content)
        if not scores:
            return 0.0
        # Hard gate: any prohibited_content failure forces a sub-threshold score
        # regardless of the average so the consumer never marks it verified.
        prohibited = float(scores.get("prohibited_content", 1.0))
        if prohibited < 0.95:
            return round(min(0.5, prohibited), 2)
        avg = sum(float(v) for v in scores.values()) / len(scores)
        return round(avg, 2)
    except Exception:
        return 0.5


def compute_community_score(times_suggested: int, times_completed: int, times_liked: int, avg_rating: float) -> float:
    if times_suggested < 5:
        return 0.7  # not enough data

    completion_rate = times_completed / times_suggested if times_suggested > 0 else 0
    like_rate = times_liked / times_suggested if times_suggested > 0 else 0
    rating_score = avg_rating / 5.0 if avg_rating > 0 else 0.5

    return round(0.3 * completion_rate + 0.3 * like_rate + 0.4 * rating_score, 2)
