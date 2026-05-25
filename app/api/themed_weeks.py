from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.activity import ThemedWeek
from app.models.user import User
from app.schemas.activity import ThemedWeekResponse

router = APIRouter(prefix="/themed-weeks", tags=["themed-weeks"])


@router.get("/", response_model=list[ThemedWeekResponse])
async def list_themed_weeks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ThemedWeek).order_by(ThemedWeek.title_en))
    return result.scalars().all()


@router.get("/{week_id}", response_model=ThemedWeekResponse)
async def get_themed_week(
    week_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ThemedWeek).where(ThemedWeek.id == week_id))
    week = result.scalar_one_or_none()
    if not week:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Themed week not found")
    return week
