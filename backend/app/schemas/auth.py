from pydantic import BaseModel

from app.models.enums import RoleName
from app.schemas.common import Email, NonEmptyStr, ORMModel


class LoginRequest(BaseModel):
    email: Email
    password: NonEmptyStr


class CurrentUser(ORMModel):
    id: int
    email: str
    full_name: str
    role: RoleName


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: CurrentUser
