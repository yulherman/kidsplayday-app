"""Streak tracking + milestone notifications."""
import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.streak import PushToken, UserStreak
from app.services.notifications import get_streak_notification
from app.services.push import send_push

logger = logging.getLogger(__name__)

MILESTONES = (3, 7, 14, 30, 60, 100, 365)


async def update_streak(
    db: AsyncSession,
    user_id: uuid.UUID,
    activity_date: date,
    user_language: str,
) -> UserStreak:
    """Update user streak after a completed activity. Sends milestone push if reached."""
    result = await db.execute(select(UserStreak).where(UserStreak.user_id == user_id))
    streak = result.scalar_one_or_none()

    if streak is None:
        streak = UserStreak(
            user_id=user_id,
            current_streak_days=1,
            longest_streak=1,
            last_activity_date=activity_date,
            last_milestone_notified=0,
        )
        db.add(streak)
    else:
        last = streak.last_activity_date
        if last == activity_date:
            return streak
        if last == activity_date - timedelta(days=1):
            streak.current_streak_days += 1
        else:
            streak.current_streak_days = 1
            streak.last_milestone_notified = 0
        streak.last_activity_date = activity_date
        if streak.current_streak_days > streak.longest_streak:
            streak.longest_streak = streak.current_streak_days

    await db.flush()

    if (
        streak.current_streak_days in MILESTONES
        and streak.current_streak_days > streak.last_milestone_notified
    ):
        await _notify_milestone(db, user_id, streak.current_streak_days, user_language)
        streak.last_milestone_notified = streak.current_streak_days
        await db.flush()

    return streak


async def _notify_milestone(
    db: AsyncSession,
    user_id: uuid.UUID,
    days: int,
    language: str,
) -> None:
    payload = get_streak_notification(language, days)
    if not payload:
        return
    tokens_result = await db.execute(
        select(PushToken.token).where(PushToken.user_id == user_id)
    )
    tokens = [r[0] for r in tokens_result.all()]
    if not tokens:
        return
    try:
        await send_push(
            tokens,
            title=payload["title"],
            body=payload["body"],
            data={"type": "streak", "days": days},
        )
    except Exception:
        logger.exception("Failed to send streak push user=%s", user_id)
