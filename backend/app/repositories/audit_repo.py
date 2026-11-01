from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent


def list_for_project(db: Session, project_id: int) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.project_id == project_id)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        )
    )
