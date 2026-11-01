from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Client


def get(db: Session, client_id: int) -> Client | None:
    return db.get(Client, client_id)


def get_by_name(db: Session, legal_entity_name: str) -> Client | None:
    return db.scalar(select(Client).where(func.lower(Client.legal_entity_name) == legal_entity_name.lower()))


def list_clients(db: Session, search: str | None = None) -> list[Client]:
    stmt = select(Client).order_by(Client.legal_entity_name)
    if search:
        stmt = stmt.where(Client.legal_entity_name.ilike(f"%{search}%"))
    return list(db.scalars(stmt))
