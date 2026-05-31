from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import Child, User
from app.schemas.user import ChildCreate, ChildResponse

router = APIRouter(prefix="/children", tags=["children"])


MAX_CHILDREN = 2


@router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
async def add_child(
    data: ChildCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Child).where(Child.user_id == user.id))
    if len(existing.scalars().all()) >= MAX_CHILDREN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {MAX_CHILDREN} children allowed per account.",
        )
    child = Child(user_id=user.id, birth_date=data.birth_date)
    db.add(child)
    await db.flush()
    return ChildResponse(
        id=child.id,
        birth_date=child.birth_date,
        age_months=child.age_months,
        age_category=child.age_category,
    )


@router.get("", response_model=list[ChildResponse])
async def list_children(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Child).where(Child.user_id == user.id))
    children = result.scalars().all()
    return [
        ChildResponse(
            id=c.id,
            birth_date=c.birth_date,
            age_months=c.age_months,
            age_category=c.age_category,
        )
        for c in children
    ]


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child(
    child_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Child).where(Child.id == child_id, Child.user_id == user.id)
    )
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    await db.delete(child)
