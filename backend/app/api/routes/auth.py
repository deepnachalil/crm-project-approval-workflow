from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DbSession
from app.schemas.auth import CurrentUser, LoginRequest, LoginResponse
from app.security.auth_provider import get_auth_provider

router = APIRouter(prefix="/auth", tags=["auth"])


def _current(user) -> CurrentUser:
    return CurrentUser(id=user.id, email=user.email, full_name=user.full_name, role=user.role_name)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: DbSession) -> LoginResponse:
    token, expires_in, user = get_auth_provider().login(db, body.email, body.password)
    return LoginResponse(access_token=token, expires_in=expires_in, user=_current(user))


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUserDep) -> CurrentUser:
    return _current(user)
