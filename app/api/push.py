from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.streak import PushToken
from app.models.user import User

router = APIRouter(prefix="/push", tags=["push"])


class PushRegisterRequest(BaseModel):
    token: str = Field(min_length=10, max_length=255)
    platform: str = Field(pattern="^(ios|android)$")


@router.post("/register")
async def register_push_token(
    data: PushRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not data.token.startswith("ExponentPushToken"):
        raise HTTPException(status_code=400, detail="Invalid Expo push token format")

    existing = await db.execute(
        select(PushToken).where(
            PushToken.user_id == user.id,
            PushToken.token == data.token,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "ok", "registered": False}

    db.add(PushToken(user_id=user.id, token=data.token, platform=data.platform))
    return {"status": "ok", "registered": True}


@router.delete("/register")
async def unregister_push_token(
    data: PushRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PushToken).where(
            PushToken.user_id == user.id,
            PushToken.token == data.token,
        )
    )
    token = result.scalar_one_or_none()
    if token:
        await db.delete(token)
    return {"status": "ok"}
