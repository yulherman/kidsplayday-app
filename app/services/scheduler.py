"""Lightweight asyncio scheduler for periodic background jobs.

Runs in the main process. If FastAPI is scaled horizontally,
guard with a Redis lock or move to a dedicated worker.
"""
import asyncio
import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from app.db.database import async_session
from app.models.streak import PushToken
from app.models.user import User
from app.services.notifications import get_morning_notification
from app.services.push import send_push

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 15 * 60  # every 15 minutes
TARGET_HOUR_LOCAL = 9  # 9 AM local time
WINDOW_MINUTES = 15  # send if current local time is within [9:00, 9:15)


async def _send_morning_reminders() -> None:
    sent_users = 0
    async with async_session() as db:
        result = await db.execute(
            select(User.id, User.language, User.timezone).where(
                User.id.in_(select(PushToken.user_id).distinct())
            )
        )
        rows = result.all()
        now_utc = datetime.utcnow()
        for user_id, language, tz_name in rows:
            try:
                tz = ZoneInfo(tz_name or "UTC")
            except ZoneInfoNotFoundError:
                tz = ZoneInfo("UTC")
            local = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
            if local.hour != TARGET_HOUR_LOCAL or local.minute >= WINDOW_MINUTES:
                continue

            tokens_result = await db.execute(
                select(PushToken.token).where(PushToken.user_id == user_id)
            )
            tokens = [r[0] for r in tokens_result.all()]
            if not tokens:
                continue

            variant_index = random.randint(0, 2)
            payload = get_morning_notification(language or "en", variant_index)
            await send_push(
                tokens,
                title=payload["title"],
                body=payload["body"],
                data={"type": "morning"},
            )
            sent_users += 1

    if sent_users:
        logger.info("Morning reminders sent to %d users", sent_users)


async def _loop() -> None:
    while True:
        try:
            await _send_morning_reminders()
        except Exception:
            logger.exception("Morning reminder loop error")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start(loop_task_holder: list) -> None:
    """Start the scheduler. Pass a list to hold the task ref so it isn't GC'd."""
    task = asyncio.create_task(_loop())
    loop_task_holder.append(task)
