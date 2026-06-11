"""
Premium/subscription management.
RevenueCat webhook endpoint + premium check middleware.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.activity import UserActivityHistory
from app.models.user import User
from app.services.plan_quota import get_plan_quota_state

router = APIRouter(prefix="/premium", tags=["premium"])

FREE_DAILY_LIMIT = 5  # free users get 5 plan generations per day (raised for v1.0 launch)
PREMIUM_MONTHLY_LIMIT = 50


def _month_start() -> datetime:
    return datetime.combine(
        date.today().replace(day=1),
        datetime.min.time(),
    ).replace(tzinfo=timezone.utc)


async def count_plans_this_month(user_id, db: AsyncSession) -> int:
    """Count total plan generations this calendar month."""
    result = await db.execute(
        select(func.count(UserActivityHistory.id)).where(
            UserActivityHistory.user_id == user_id,
            UserActivityHistory.status == "suggested",
            UserActivityHistory.suggested_at >= _month_start(),
        )
    )
    return result.scalar() or 0


async def check_premium_or_limit(user: User, db: AsyncSession) -> bool:
    """Raise 403 if user exceeded free daily or premium monthly plan limits."""
    if user.is_premium_active:
        plan_count = await count_plans_this_month(user.id, db)
        if plan_count >= PREMIUM_MONTHLY_LIMIT:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Monthly plan limit reached ({PREMIUM_MONTHLY_LIMIT}). "
                    "Limit resets next month."
                ),
            )
        return True

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    result = await db.execute(
        select(func.count()).where(
            UserActivityHistory.user_id == user.id,
            UserActivityHistory.suggested_at >= today_start,
        )
    )
    count = result.scalar()
    if count and count >= FREE_DAILY_LIMIT * 5:  # ~5 activities per generation
        raise HTTPException(
            status_code=403,
            detail="Free plan limit reached. Upgrade to Premium for unlimited activities.",
        )
    return False


@router.get("/status")
async def premium_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active = user.is_premium_active
    plans_used = await count_plans_this_month(user.id, db)
    quota = await get_plan_quota_state(user)
    return {
        "is_premium": active,
        "plan": "premium" if active else "free",
        "source": "subscription" if user.is_premium else ("bonus" if active else None),
        "premium_until": user.premium_until.isoformat() if user.premium_until else None,
        "daily_limit": None if active else FREE_DAILY_LIMIT,
        "monthly_limit": PREMIUM_MONTHLY_LIMIT if active else None,
        "plans_used_this_month": plans_used if active else None,
        "daily_plans_used": quota["used"],
        "daily_plans_limit": quota["limit"],
        "daily_plans_remaining": quota["remaining"],
        "daily_resets_in_seconds": quota["resets_in_seconds"],
    }


@router.post("/webhook/revenuecat")
async def revenuecat_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """
    RevenueCat server-to-server webhook.
    Receives subscription events and updates user premium status.
    Docs: https://www.revenuecat.com/docs/integrations/webhooks
    """
    expected = settings.revenuecat_webhook_secret
    if not expected:
        raise HTTPException(status_code=500, detail="webhook secret not configured")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="invalid webhook authorization")

    body = await request.json()
    event = body.get("event", {})
    event_type = event.get("type", "")
    app_user_id = event.get("app_user_id", "")

    if not app_user_id:
        return {"status": "ignored", "reason": "no app_user_id"}

    from uuid import UUID
    try:
        user_id = UUID(app_user_id)
    except ValueError:
        return {"status": "ignored", "reason": "invalid user_id"}

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"status": "ignored", "reason": "user not found"}

    activate_events = {
        "INITIAL_PURCHASE",
        "RENEWAL",
        "UNCANCELLATION",
        "NON_RENEWING_PURCHASE",
    }
    deactivate_events = {
        "CANCELLATION",
        "EXPIRATION",
        "BILLING_ISSUE",
    }

    if event_type in activate_events:
        user.is_premium = True
        expiration_ms = event.get("expiration_at_ms")
        if expiration_ms:
            user.premium_until = datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc)
    elif event_type in deactivate_events:
        user.is_premium = False

    await db.commit()
    return {"status": "ok", "event": event_type, "premium": user.is_premium}
