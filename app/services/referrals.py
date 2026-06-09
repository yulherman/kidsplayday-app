"""Referral code generation."""
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 8


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


async def assign_referral_code(db: AsyncSession, user: User) -> str:
    """Generate a unique referral code for the user, retrying on collision."""
    for _ in range(5):
        code = generate_code()
        existing = await db.execute(select(User.id).where(User.referral_code == code))
        if existing.scalar_one_or_none() is None:
            user.referral_code = code
            return code
    raise RuntimeError("Could not generate unique referral code after 5 attempts")
