from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditAction, AuditEvent, ProjectVersion, User


def record(
    db: Session,
    *,
    user: User,
    action: AuditAction,
    project_id: int | None = None,
    version: ProjectVersion | None = None,
    client_id: int | None = None,
    comment: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append an audit event to the current transaction (committed with the change it describes)."""
    if version is not None:
        if version.id is None:
            db.flush()  # assign ids to rows created earlier in this transaction
        details = {"version_number": version.version_number, **(details or {})}
    event = AuditEvent(
        project_id=project_id if project_id is not None else (version.project_id if version else None),
        version_id=version.id if version else None,
        client_id=client_id,
        user_id=user.id,
        action=action,
        comment=comment,
        details=details,
    )
    db.add(event)
    return event
