"""HS256 JWTs signed with JWT_SECRET: session tokens (local auth mode) and
short-lived download tokens (local storage mode)."""
from datetime import timedelta
from typing import Any

import jwt

from app.config import get_settings
from app.errors import AuthenticationError
from app.models.base import utcnow

_ISSUER = "crm-projects-api"
SESSION_AUDIENCE = "crm-projects-session"
DOWNLOAD_AUDIENCE = "crm-projects-download"


def _secret() -> str:
    secret = get_settings().jwt_secret
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")
    return secret


def encode_token(subject: str, audience: str, ttl: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = utcnow()
    payload = {"sub": subject, "aud": audience, "iss": _ISSUER, "iat": now, "exp": now + ttl, **(extra or {})}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str, audience: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"], audience=audience, issuer=_ISSUER)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid token") from exc
