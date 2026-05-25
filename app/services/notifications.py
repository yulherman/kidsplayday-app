"""
Push notification templates for daily engagement.
In production, integrate with Firebase Cloud Messaging or Expo Push.
"""

MORNING_NOTIFICATIONS = {
    "en": [
        {"title": "Good morning! ☀️", "body": "Today's activity plan is ready. Let's play!"},
        {"title": "New adventures await! 🎨", "body": "Check today's activities for your kids."},
        {"title": "PlayDay time! 🎯", "body": "Fresh activities generated just for your family."},
    ],
    "uk": [
        {"title": "Доброго ранку! ☀️", "body": "План активностей на сьогодні готовий. Грати!"},
        {"title": "Нові пригоди чекають! 🎨", "body": "Перевірте сьогоднішні активності для ваших дітей."},
        {"title": "Час PlayDay! 🎯", "body": "Свіжі активності згенеровані спеціально для вашої родини."},
    ],
}

EVENING_REMINDERS = {
    "en": [
        {"title": "How was today? ⭐", "body": "Rate today's activities to get better recommendations tomorrow."},
    ],
    "uk": [
        {"title": "Як пройшов день? ⭐", "body": "Оцініть сьогоднішні активності для кращих рекомендацій завтра."},
    ],
}

STREAK_NOTIFICATIONS = {
    "en": {
        3: {"title": "3-day streak! 🔥", "body": "You're on a roll! Keep the fun going."},
        7: {"title": "7-day streak! 🏆", "body": "A whole week of activities! Your kids are loving it."},
        14: {"title": "2-week champion! 🎖️", "body": "14 days of PlayDay! You're an amazing parent."},
        30: {"title": "Monthly master! 👑", "body": "30 days! You've unlocked the Super Family badge."},
    },
    "uk": {
        3: {"title": "3 дні поспіль! 🔥", "body": "Чудово! Продовжуйте веселощі."},
        7: {"title": "7 днів поспіль! 🏆", "body": "Цілий тиждень активностей! Ваші діти в захваті."},
        14: {"title": "Чемпіон 2 тижнів! 🎖️", "body": "14 днів PlayDay! Ви неймовірні батьки."},
        30: {"title": "Майстер місяця! 👑", "body": "30 днів! Ви отримали бейдж Суперсім'ї."},
    },
}


def get_morning_notification(language: str, day_index: int = 0) -> dict:
    lang = language if language in MORNING_NOTIFICATIONS else "en"
    notifications = MORNING_NOTIFICATIONS[lang]
    return notifications[day_index % len(notifications)]


def get_streak_notification(language: str, streak_days: int) -> dict | None:
    lang = language if language in STREAK_NOTIFICATIONS else "en"
    return STREAK_NOTIFICATIONS[lang].get(streak_days)
