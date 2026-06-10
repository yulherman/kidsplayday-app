"""Per-user daily plan-generation quota stored in Redis, with reset at
midnight in the user's timezone."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import redis.asyncio as aioredis
import redis.exceptions
from fastapi import HTTPException

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

FREE_DAILY_PLANS = 1
PREMIUM_DAILY_PLANS = 3
_TTL_BUFFER_SECONDS = 3600  # 1h padding past midnight


def _user_tz(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _user_today_str(user: User) -> str:
    return datetime.now(_user_tz(user)).strftime("%Y-%m-%d")


def _seconds_until_next_midnight(user: User) -> int:
    tz = _user_tz(user)
    now = datetime.now(tz)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((tomorrow - now).total_seconds()) + _TTL_BUFFER_SECONDS


def _quota_key(user: User) -> str:
    return f"plan:gen:{user.id}:{_user_today_str(user)}"


def daily_limit_for(user: User) -> int:
    return PREMIUM_DAILY_PLANS if user.is_premium_active else FREE_DAILY_PLANS


async def _open_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def assert_plan_quota(user: User) -> None:
    """Raise HTTP 429 if the user has reached the daily plan-generation limit."""
    limit = daily_limit_for(user)
    key = _quota_key(user)
    client = await _open_redis()
    try:
        raw = await client.get(key)
        used = int(raw) if raw else 0
    except redis.exceptions.RedisError as exc:
        logger.warning("Redis unavailable (assert_plan_quota), allowing through: %s", exc)
        return
    finally:
        try:
            await client.aclose()
        except Exception:
            pass
    if used >= limit:
        plan_label = "Premium" if user.is_premium_active else "Free"
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily plan limit reached ({limit}/day for {plan_label}). "
                "Resets at midnight in your local time."
            ),
        )


async def increment_plan_quota(user: User) -> int:
    """Atomically increment today's counter; set TTL only on the first call."""
    key = _quota_key(user)
    ttl = _seconds_until_next_midnight(user)
    client = await _open_redis()
    try:
        new_val = await client.incr(key)
        if new_val == 1:
            await client.expire(key, ttl)
        return int(new_val)
    except redis.exceptions.RedisError as exc:
        logger.warning("Redis unavailable (increment_plan_quota): %s", exc)
        return 0
    finally:
        try:
            await client.aclose()
        except Exception:
            pass


async def get_plan_quota_state(user: User) -> dict:
    """Return current daily-quota state for the user (used/limit/remaining/reset)."""
    key = _quota_key(user)
    limit = daily_limit_for(user)
    client = await _open_redis()
    used = 0
    try:
        raw = await client.get(key)
        used = int(raw) if raw else 0
    except redis.exceptions.RedisError as exc:
        logger.warning("Redis unavailable (get_plan_quota_state): %s", exc)
    finally:
        try:
            await client.aclose()
        except Exception:
            pass
    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "resets_in_seconds": _seconds_until_next_midnight(user) - _TTL_BUFFER_SECONDS,
    }
