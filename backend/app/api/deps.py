from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RoleName, User
from app.security.auth_provider import get_auth_provider
from app.services.policies import ensure_role

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    return get_auth_provider().authenticate(db, request)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_role(*roles: RoleName):
    """Route-level role guard. Services re-check roles as defence in depth."""

    def dependency(user: CurrentUserDep) -> User:
        ensure_role(user, *roles)
        return user

    return Depends(dependency)


CrmUser = Annotated[User, require_role(RoleName.CRM)]
ApproverUser = Annotated[User, require_role(RoleName.APPROVER)]
