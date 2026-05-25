"""
Safety validator that checks each AI-generated activity against
age-specific rules before it reaches the user.
"""

import logging

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


def validate_activity(activity_data: dict, child_age_months: int) -> tuple[bool, list[str]]:
    issues = []

    materials = activity_data.get("materials_needed", [])
    if isinstance(materials, str):
        materials = [materials]

    for age_threshold, blacklisted in MATERIAL_BLACKLIST_BY_AGE.items():
        if child_age_months < age_threshold:
            for material in materials:
                material_lower = material.lower()
                for banned in blacklisted:
                    if banned in material_lower:
                        issues.append(f"Material '{material}' not safe for children under {age_threshold} months")
            break

    # try:
    #     duration = int(activity_data.get("duration_minutes", 0))
    # except (ValueError, TypeError):
    #     duration = 0
    # for age_threshold, max_dur in sorted(MAX_DURATION_BY_AGE.items()):
    #     if child_age_months < age_threshold:
    #         if duration > max_dur:
    #             issues.append(f"Duration {duration}min too long for children under {age_threshold} months (max {max_dur})")
    #         break

    instructions_en = activity_data.get("instructions_en", "").lower()
    instructions_uk = activity_data.get("instructions_uk", "").lower()
    all_text = instructions_en + " " + instructions_uk
    has_supervision = any(kw in all_text for kw in SUPERVISION_KEYWORDS)
    if not has_supervision:
        logger.warning(
            "Missing adult supervision note in instructions (warning only): title=%s",
            activity_data.get("title_en") or activity_data.get("title_uk"),
        )

    return len(issues) == 0, issues
