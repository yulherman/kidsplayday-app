"""Sign in with Apple — verify identity tokens via Apple JWKS."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

_apple_jwks_cache: dict[str, Any] | None = None
_apple_jwks_lock = asyncio.Lock()


async def _get_apple_jwks() -> dict[str, Any]:
    global _apple_jwks_cache
    if _apple_jwks_cache is not None:
        return _apple_jwks_cache
    async with _apple_jwks_lock:
        if _apple_jwks_cache is not None:
            return _apple_jwks_cache
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(APPLE_JWKS_URL)
            resp.raise_for_status()
            _apple_jwks_cache = resp.json()
    return _apple_jwks_cache


async def verify_apple_identity_token(token: str) -> dict[str, Any]:
    if not settings.apple_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apple Sign-In not configured",
        )
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Malformed Apple token") from exc

    kid = unverified_header.get("kid")
    jwks = await _get_apple_jwks()
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        global _apple_jwks_cache
        _apple_jwks_cache = None
        jwks = await _get_apple_jwks()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        raise HTTPException(status_code=401, detail="Unknown Apple signing key")

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=settings.apple_client_id,
            issuer=APPLE_ISSUER,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Apple token") from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Apple token missing subject")
    return {"sub": sub, "email": payload.get("email")}


async def get_or_create_apple_user(
    db: AsyncSession,
    *,
    subject: str,
    email: str | None,
    name: str | None,
    language: str,
    country: str | None = None,
) -> User:
    conditions = [User.apple_subject == subject]
    if email:
        conditions.append(User.email == email)
    result = await db.execute(select(User).where(or_(*conditions)))
    user = result.scalars().first()

    if user is None:
        if not email:
            raise HTTPException(status_code=400, detail="Apple did not provide an email")
        user = User(
            email=email,
            language=language,
            country=country,
            name=name,
            apple_subject=subject,
        )
        db.add(user)
        await db.flush()
        from app.services.referrals import assign_referral_code
        await assign_referral_code(db, user)
        await db.flush()
        return user

    if user.apple_subject != subject:
        user.apple_subject = subject
    if name and not user.name:
        user.name = name
    await db.flush()
    return user
