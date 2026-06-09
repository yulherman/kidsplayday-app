from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.streak import UserStreak
from app.models.user import User

router = APIRouter(prefix="/streak", tags=["streak"])


@router.get("")
async def get_streak(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserStreak).where(UserStreak.user_id == user.id))
    streak = result.scalar_one_or_none()
    if streak is None:
        return {
            "current_streak_days": 0,
            "longest_streak": 0,
            "last_activity_date": None,
        }
    return {
        "current_streak_days": streak.current_streak_days,
        "longest_streak": streak.longest_streak,
        "last_activity_date": streak.last_activity_date.isoformat() if streak.last_activity_date else None,
    }
