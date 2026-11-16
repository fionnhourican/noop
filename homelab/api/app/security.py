"""Security and authentication utilities."""

import secrets
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_ingestion_token(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> str:
    """Validate Bearer token for the Windows collector ingestion endpoint.

    Uses constant-time comparison to prevent timing attacks.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_token = settings.INGESTION_TOKEN.get_secret_value()
    provided_token = credentials.credentials

    # Constant time comparison
    if not secrets.compare_digest(provided_token.encode("utf-8"), expected_token.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid ingestion token",
        )

    return provided_token


async def get_current_dashboard_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> str:
    """Validate token for browser dashboard queries."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dashboard authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_token = settings.DASHBOARD_TOKEN.get_secret_value()
    provided_token = credentials.credentials

    if not secrets.compare_digest(provided_token.encode("utf-8"), expected_token.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid dashboard token",
        )

    return provided_token
