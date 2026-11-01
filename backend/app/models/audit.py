from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin
from app.models.enums import AuditAction
from app.models.project import ProjectVersion
from app.models.user import User


class AuditEvent(CreatedAtMixin, Base):
    """Append-only audit log. Rows are never updated or deleted by the application."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_project_created", "project_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    version_id: Mapped[int | None] = mapped_column(ForeignKey("project_versions.id", ondelete="SET NULL"))
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, native_enum=False, length=64, name="audit_action"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))

    user: Mapped[User] = relationship(lazy="joined")
    version: Mapped[ProjectVersion | None] = relationship(lazy="joined")
