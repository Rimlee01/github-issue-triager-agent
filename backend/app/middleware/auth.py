"""
API key authentication middleware.

Decision: simple API key in header rather than JWT for this project.
JWT is overkill when the consumer is a single frontend dashboard —
API key is easier to rotate and reason about. In production, set
ENABLE_AUTH=true and rotate the API_KEY from the default.
"""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings

settings = get_settings()
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not settings.ENABLE_AUTH:
        return "no-auth"
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass it in the X-API-Key header.",
        )
    return api_key
