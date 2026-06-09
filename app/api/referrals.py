from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.referrals import assign_referral_code

router = APIRouter(prefix="/referrals", tags=["referrals"])

BONUS_DAYS = 7


class RedeemRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


@router.get("/me")
async def my_referral(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.referral_code:
        await assign_referral_code(db, user)

    signups_result = await db.execute(
        select(func.count()).where(User.referred_by_user_id == user.id)
    )
    signups = signups_result.scalar() or 0

    return {
        "code": user.referral_code,
        "signups_count": signups,
        "premium_days_earned": signups * BONUS_DAYS,
        "premium_until": user.premium_until.isoformat() if user.premium_until else None,
    }


@router.post("/redeem")
async def redeem_referral(
    data: RedeemRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.referred_by_user_id is not None:
        raise HTTPException(status_code=400, detail="You have already redeemed a referral code")

    code = data.code.strip().upper()
    if user.referral_code and code == user.referral_code:
        raise HTTPException(status_code=400, detail="Cannot redeem your own code")

    result = await db.execute(select(User).where(User.referral_code == code))
    referrer = result.scalar_one_or_none()
    if referrer is None:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if referrer.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot redeem your own code")

    now = datetime.now(timezone.utc)
    extension = timedelta(days=BONUS_DAYS)
    for u in (user, referrer):
        base = u.premium_until if u.premium_until and u.premium_until > now else now
        u.premium_until = base + extension

    user.referred_by_user_id = referrer.id

    return {
        "status": "ok",
        "bonus_days": BONUS_DAYS,
        "premium_until": user.premium_until.isoformat(),
    }
