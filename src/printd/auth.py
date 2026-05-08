"""Bearer-token auth dependency."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .config import Settings


def make_auth_dependency(settings: Settings):
    expected = settings.api_key

    def require_bearer(authorization: str | None = Header(default=None)) -> None:
        if not expected:
            return  # dev mode: no key configured
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": 'Bearer realm="printd"'},
            )
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Expected `Authorization: Bearer <key>`",
            )
        if not hmac.compare_digest(token, expected):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")

    return require_bearer
