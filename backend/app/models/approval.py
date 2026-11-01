from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, utcnow
from app.models.enums import ApprovalStatus, CommentKind
from app.models.project import ProjectVersion
from app.models.user import User


class ApprovalRequest(Base):
    """One submission of a project version for approval and its decision."""

    __tablename__ = "approval_requests"
    __table_args__ = (Index("ix_approval_requests_approver_status", "approver_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[int] = mapped_column(
        ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False, length=32, name="approval_status"),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )
    is_resubmission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    version: Mapped[ProjectVersion] = relationship(lazy="joined")
    submitted_by: Mapped[User] = relationship(foreign_keys=[submitted_by_id], lazy="joined")
    approver: Mapped[User] = relationship(foreign_keys=[approver_id], lazy="joined")
    decided_by: Mapped[User | None] = relationship(foreign_keys=[decided_by_id], lazy="joined")
    comments: Mapped[list["ApprovalComment"]] = relationship(
        back_populates="approval_request", order_by="ApprovalComment.id", cascade="all, delete-orphan"
    )

    def comment_of(self, kind: CommentKind) -> str | None:
        return next((c.comment for c in self.comments if c.kind == kind), None)


class ApprovalComment(CreatedAtMixin, Base):
    __tablename__ = "approval_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    approval_request_id: Mapped[int] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[CommentKind] = mapped_column(
        Enum(CommentKind, native_enum=False, length=32, name="comment_kind"), nullable=False
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    approval_request: Mapped[ApprovalRequest] = relationship(back_populates="comments")
    author: Mapped[User] = relationship(lazy="joined")
