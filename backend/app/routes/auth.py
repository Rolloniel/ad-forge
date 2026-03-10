from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models.user import ApiKey, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthValidateRequest(BaseModel):
    api_key: str


class AuthValidateResponse(BaseModel):
    valid: bool
    user_name: str


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def _lookup_user_by_key(session: AsyncSession, raw_key: str) -> User | None:
    """Look up a user by raw API key. Returns None if key is invalid/expired/revoked."""
    key_hash = _hash_key(raw_key)
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(ApiKey)
        .where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active.is_(True),
            ApiKey.expires_at > now,
        )
        .options(selectinload(ApiKey.user))
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        return None
    return api_key.user


@router.post("/validate", response_model=AuthValidateResponse)
async def validate_api_key(
    body: AuthValidateRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await _lookup_user_by_key(session, body.api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )
    return AuthValidateResponse(valid=True, user_name=user.name)


async def require_auth(
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dependency that verifies Bearer token and returns the User."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer scheme",
        )
    token = authorization.removeprefix("Bearer ")
    user = await _lookup_user_by_key(session, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user
