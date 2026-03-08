from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthValidateRequest(BaseModel):
    api_key: str


class AuthValidateResponse(BaseModel):
    valid: bool
    token: str


@router.post("/validate", response_model=AuthValidateResponse)
async def validate_api_key(body: AuthValidateRequest):
    if body.api_key != settings.adforge_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return AuthValidateResponse(valid=True, token=body.api_key)


async def require_auth(authorization: str = Header(...)) -> str:
    """Dependency that verifies Bearer token on protected routes."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer scheme",
        )
    token = authorization.removeprefix("Bearer ")
    if token != settings.adforge_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return token
