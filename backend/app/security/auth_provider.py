"""Pluggable authentication.

* LocalAuthProvider   - email/password against the users table; issues HS256 JWTs.
* CognitoAuthProvider - used on AWS. The API Gateway Cognito authorizer has
  already verified the ID token signature/expiry before the request reaches
  Lambda; we read the verified claims from the API Gateway event and map the
  email claim to an active user row. Roles are always taken from the database,
  so authorization is enforced by this API regardless of identity provider.
"""
from datetime import timedelta
from typing import Protocol

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AppError, AuthenticationError
from app.models import User
from app.repositories import user_repo
from app.security.passwords import verify_password
from app.security.tokens import SESSION_AUDIENCE, decode_token, encode_token


class AuthProvider(Protocol):
    def login(self, db: Session, email: str, password: str) -> tuple[str, int, User]: ...

    def authenticate(self, db: Session, request: Request) -> User: ...


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Missing bearer token")
    return token


def _active_user(user: User | None) -> User:
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


class LocalAuthProvider:
    def login(self, db: Session, email: str, password: str) -> tuple[str, int, User]:
        user = user_repo.get_by_email(db, email)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        ttl_seconds = get_settings().jwt_expires_minutes * 60
        token = encode_token(str(user.id), SESSION_AUDIENCE, timedelta(seconds=ttl_seconds))
        return token, ttl_seconds, user

    def authenticate(self, db: Session, request: Request) -> User:
        claims = decode_token(_bearer_token(request), SESSION_AUDIENCE)
        return _active_user(db.get(User, int(claims["sub"])))


class CognitoAuthProvider:
    def login(self, db: Session, email: str, password: str) -> tuple[str, int, User]:
        raise AppError("Login is handled by Amazon Cognito when AUTH_MODE=cognito")

    def authenticate(self, db: Session, request: Request) -> User:
        event = request.scope.get("aws.event") or {}
        claims = (event.get("requestContext") or {}).get("authorizer", {}).get("claims") or {}
        email = claims.get("email")
        if not email:
            raise AuthenticationError("Missing Cognito identity")
        return _active_user(user_repo.get_by_email(db, email))


def get_auth_provider() -> AuthProvider:
    return CognitoAuthProvider() if get_settings().auth_mode == "cognito" else LocalAuthProvider()
