"""
Safety validator that checks each AI-generated activity against
age-specific rules before it reaches the user.

The validator applies two policies in one pass:
- Hard rejection for unfixable issues (banned materials, prohibited topics).
- In-place auto-fix for issues that can be patched safely without a regen
  (evaluative praise → process-praise; missing supervision note → inserted
  into an existing step; allergen present → ⚠ marker injected).
"""

import logging
import re

logger = logging.getLogger(__name__)

SUPERVISION_KEYWORDS = (
    "supervision",
    "supervise",
    "supervised",
    "adult",
    "parent",
    "caregiver",
    "guardian",
    "watch",
    "нагляд",
    "дорослий",
    "батьк",
    "під контролем",
)

MATERIAL_BLACKLIST_BY_AGE = {
    12: [  # under 1 year
        "scissors", "beads", "small parts", "coins", "buttons", "balloons",
        "sharp", "knife", "glass", "oven", "stove", "hot glue",
        "markers", "paint (non-edible)", "string", "rope", "plastic bag",
    ],
    24: [  # under 2 years
        "scissors", "beads", "small parts", "coins", "buttons",
        "sharp", "knife", "glass", "oven", "stove", "hot glue",
        "string longer than 15cm", "plastic bag",
    ],
    36: [  # under 3 years
        "scissors (adult)", "sharp", "knife", "glass",
        "oven", "stove", "hot glue", "small magnets",
    ],
    72: [  # under 6 years
        "sharp knife", "glass", "oven (unsupervised)",
        "power tools", "hot glue gun (unsupervised)",
    ],
    108: [  # under 9 years
        "power tools", "sharp knife (unsupervised)",
    ],
    144: [  # under 12 years
        "power tools (unsupervised)",
    ],
}

MAX_DURATION_BY_AGE = {
    12: 15,
    24: 20,
    36: 30,
    48: 40,
    72: 60,
    108: 90,
    144: 120,
}

# Prohibited topical content. Keyword match anywhere in title + short_desc +
# description + instructions triggers rejection. Lower-cased before compare.
# Sub-strings are intentional: "knife fight" matches but "butter knife" does
# not (it would only match "knife" if we listed bare "knife" — we don't here
# because materials validator handles tool safety).
PROHIBITED_KEYWORDS: dict[str, list[str]] = {
    "weapons_violence": [
        "weapon", "gun ", "pistol", "rifle", "machine gun", "sword fight",
        "shoot at", "kill ", "attack ", "fight off", "war ",
        "зброя", "пістолет", "ніж бій", "вбити", "стріляти", "війна", "битися",
    ],
    "fear_horror": [
        "ghost", "haunted", "scary", "horror", "die ", "death", "funeral",
        "kidnap", "monster",
        "привид", "монстр", "страшний", "смерть", "померти", "похорон",
    ],
    "religion_politics": [
        "pray ", "prayer", "church mass", "sermon", "proselyt",
        "president ", "election", "political party",
        "молитва", "церковна служба", "проповідь",
        "президент ", "вибори", "політична партія",
    ],
    "addictive_substances": [
        "alcohol", "wine", "beer ", "cigarette", "smoke ", "vape", "casino",
        "place a bet", "gambling",
        "алкоголь", "вино", "пиво", "сигарет", "куріння", "казино", "ставка",
    ],
    "body_image": [
        "calorie", " diet ", "weight loss", "burn off", "skinny", "fat free",
        "калорі", "дієта", "схуднення",
    ],
    "brands": [
        "disney", "marvel", "lego ", "mcdonald", "coca-cola", "pepsi",
        "nike", "barbie", "playstation", "xbox", "nintendo",
    ],
}

# Allergens — instead of rejecting we inject a ⚠ marker into the relevant step.
ALLERGEN_KEYWORDS = [
    "peanut", "tree nut", "shellfish", "shrimp", "sesame",
    "арахіс", "горіх", "креветк", "кунжут",
]
ALLERGEN_WARNING_MARKERS = ("⚠", "allergen", "алерген")

# Evaluative praise → process-praise. Direct 1→1 mapping, deterministic,
# case-insensitive substring replacement on activity_data["instructions"].
# English and Ukrainian entries share one map: language passthrough is safe
# because English tokens won't appear in a Ukrainian-only activity and vice
# versa. Replacements were drawn from app/prompts/encouragement/{en,uk}.txt.
PRAISE_REPLACEMENTS: dict[str, str] = {
    # English
    "you're so smart": "you figured out your own way",
    "you are so smart": "you figured out your own way",
    "smart girl": "you worked through that step",
    "smart boy": "you worked through that step",
    "great job": "you stayed with it — that paid off",
    "well done": "look how that came together",
    "good job": "you kept going — that worked",
    # Ukrainian
    "молодець": "ти не здався — і в тебе вийшло",
    "молодці": "ви не здалися — і у вас вийшло",
    "розумничок": "ти знайшов свій спосіб зробити це",
    "розумниця": "ти знайшла свій спосіб зробити це",
    "чудово!": "подивися, як це склалося разом.",
    "чудово.": "подивися, як це склалося разом.",
}

SUPERVISION_NOTE_EN = "**Under adult supervision.**"
SUPERVISION_NOTE_UK = "**Під наглядом дорослого.**"

ALLERGEN_NOTE_EN = "⚠ Allergen — check before serving."
ALLERGEN_NOTE_UK = "⚠ Алерген — перевірте перед використанням."

ALLERGEN_ALT_EN = "(alternative: see ingredient swap below)"
ALLERGEN_ALT_UK = "(альтернатива: див. заміну нижче)"


def _collect_text(activity_data: dict) -> str:
    parts = [
        activity_data.get("title", ""),
        activity_data.get("short_description", ""),
        activity_data.get("description", ""),
        activity_data.get("instructions", ""),
    ]
    return " ".join(p for p in parts if p).lower()


def _instructions_text(activity_data: dict) -> str:
    return (activity_data.get("instructions") or "").lower()


def _is_uk(activity_data: dict) -> bool:
    return (activity_data.get("language") or "en").lower().startswith("uk")


def _split_steps(instructions: str) -> list[str]:
    return instructions.split("\n") if instructions else []


def _replace_praise(activity_data: dict) -> None:
    """Substitute evaluative praise with process-praise. Mutates in place."""
    instr = activity_data.get("instructions") or ""
    if not instr:
        return
    for needle, replacement in PRAISE_REPLACEMENTS.items():
        pattern = re.compile(re.escape(needle), re.IGNORECASE)
        if pattern.search(instr):
            instr = pattern.sub(replacement, instr)
            logger.info("Auto-replaced evaluative praise '%s'", needle)
    activity_data["instructions"] = instr


def _insert_supervision_note(activity_data: dict) -> None:
    """Append a supervision note to an existing instruction step. Mutates."""
    instr = activity_data.get("instructions") or ""
    steps = _split_steps(instr)
    non_empty_idxs = [i for i, s in enumerate(steps) if s.strip()]
    if not non_empty_idxs:
        return
    note = SUPERVISION_NOTE_UK if _is_uk(activity_data) else SUPERVISION_NOTE_EN
    target_idx = non_empty_idxs[2] if len(non_empty_idxs) >= 3 else non_empty_idxs[-1]
    steps[target_idx] = steps[target_idx].rstrip() + " " + note
    activity_data["instructions"] = "\n".join(steps)
    logger.info("Auto-inserted supervision note into step %d", target_idx + 1)


def _insert_allergen_warning(activity_data: dict, allergen: str) -> None:
    """Prefix the first allergen-mentioning step with a ⚠ marker. Mutates."""
    instr = activity_data.get("instructions") or ""
    steps = _split_steps(instr)
    if not steps:
        return
    target_idx = 0
    for i, step in enumerate(steps):
        if step.strip() and allergen in step.lower():
            target_idx = i
            break
    if _is_uk(activity_data):
        marker = ALLERGEN_NOTE_UK
        alt = ALLERGEN_ALT_UK
    else:
        marker = ALLERGEN_NOTE_EN
        alt = ALLERGEN_ALT_EN

    materials = activity_data.get("materials_needed") or []
    materials_text = " ".join(str(m).lower() for m in materials) if isinstance(materials, list) else ""
    needs_alt = "alternative" not in materials_text and "альтернатив" not in materials_text

    prefix = marker + (" " + alt if needs_alt else "")
    steps[target_idx] = prefix + " " + steps[target_idx].lstrip()
    activity_data["instructions"] = "\n".join(steps)
    logger.info(
        "Auto-inserted allergen warning for '%s' into step %d",
        allergen,
        target_idx + 1,
    )


def validate_activity(activity_data: dict, child_age_months: int) -> tuple[bool, list[str]]:
    issues: list[str] = []

    # -- Material blacklist by age ------------------------------------------------
    materials = activity_data.get("materials_needed", [])
    if isinstance(materials, str):
        materials = [materials]

    for age_threshold, blacklisted in MATERIAL_BLACKLIST_BY_AGE.items():
        if child_age_months < age_threshold:
            for material in materials:
                material_lower = str(material).lower()
                for banned in blacklisted:
                    if banned in material_lower:
                        issues.append(
                            f"Material '{material}' not safe for children under {age_threshold} months"
                        )
            break

    # -- Prohibited topical content ----------------------------------------------
    all_text = _collect_text(activity_data)
    for category, keywords in PROHIBITED_KEYWORDS.items():
        for kw in keywords:
            if kw in all_text:
                issues.append(f"Prohibited content ({category}): '{kw.strip()}'")

    # -- Auto-fix: evaluative praise → process praise -----------------------------
    _replace_praise(activity_data)

    # -- Auto-fix: allergen present without ⚠ marker ------------------------------
    instr_text = _instructions_text(activity_data)
    has_warning = any(marker in instr_text for marker in ALLERGEN_WARNING_MARKERS)
    if not has_warning:
        full_text = _collect_text(activity_data)
        for allergen in ALLERGEN_KEYWORDS:
            if allergen in full_text:
                _insert_allergen_warning(activity_data, allergen)
                break  # one marker covers the activity

    # -- Auto-fix: missing adult supervision note ---------------------------------
    instr_text = _instructions_text(activity_data)
    has_supervision = any(kw in instr_text for kw in SUPERVISION_KEYWORDS)
    if not has_supervision:
        _insert_supervision_note(activity_data)

    return len(issues) == 0, issues
