from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Role, RoleName, User


def get(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def list_users(db: Session, role: RoleName | None = None) -> list[User]:
    stmt = select(User).join(Role).where(User.is_active.is_(True)).order_by(User.full_name)
    if role:
        stmt = stmt.where(Role.name == role)
    return list(db.scalars(stmt))


def get_role(db: Session, name: RoleName) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name))
