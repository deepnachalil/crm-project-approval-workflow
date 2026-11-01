"""Projects and their immutable-once-approved versions.

A `Project` is a stable identity (project code, creator). All configuration lives
on `ProjectVersion` rows. Exactly one version per project may be active (the
currently approved configuration); the latest version is the one being worked on.
"""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow
from app.models.catalog import JobCategory, RateCard
from app.models.client import Client
from app.models.enums import VersionStatus
from app.models.user import User


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # Denormalised pointer to the newest version (the "current" one shown in lists).
    latest_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_by: Mapped[User] = relationship(lazy="joined")
    versions: Mapped[list["ProjectVersion"]] = relationship(
        back_populates="project", order_by="ProjectVersion.version_number", cascade="all, delete-orphan"
    )

    @property
    def latest_version(self) -> "ProjectVersion":
        return next(v for v in self.versions if v.version_number == self.latest_version_number)

    @property
    def active_version(self) -> "ProjectVersion | None":
        return next((v for v in self.versions if v.is_active), None)


class ProjectVersion(TimestampMixin, Base):
    __tablename__ = "project_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="uq_project_versions_project_version"),
        # At most one active (approved, in-effect) version per project.
        Index(
            "uq_project_versions_one_active",
            "project_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
        Index("ix_project_versions_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[VersionStatus] = mapped_column(
        Enum(VersionStatus, native_enum=False, length=32, name="version_status"),
        nullable=False,
        default=VersionStatus.DRAFT,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    based_on_version_id: Mapped[int | None] = mapped_column(ForeignKey("project_versions.id"))

    # --- Basic information ---
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    business_unit: Mapped[str | None] = mapped_column(String(128))
    crm_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), index=True)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    project: Mapped[Project] = relationship(back_populates="versions")
    client: Mapped[Client | None] = relationship(lazy="joined")
    crm_user: Mapped[User] = relationship(foreign_keys=[crm_user_id], lazy="joined")
    approver: Mapped[User | None] = relationship(foreign_keys=[approver_id], lazy="joined")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id], lazy="joined")
    based_on: Mapped["ProjectVersion | None"] = relationship(remote_side=[id])
    job_categories: Mapped[list["ProjectJobCategory"]] = relationship(
        back_populates="version", order_by="ProjectJobCategory.position", cascade="all, delete-orphan"
    )
    contracts: Mapped[list["Contract"]] = relationship(
        back_populates="version", order_by="Contract.id", cascade="all, delete-orphan"
    )

    @property
    def is_editable(self) -> bool:
        return self.status in (VersionStatus.DRAFT, VersionStatus.REJECTED)


class ProjectJobCategory(Base):
    """A job category defined on a project version, mapped to a rate card."""

    __tablename__ = "project_job_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Optional link to the standard catalog entry the name was picked from.
    job_category_id: Mapped[int | None] = mapped_column(ForeignKey("job_categories.id"))
    rate_card_id: Mapped[int | None] = mapped_column(ForeignKey("rate_cards.id"))

    version: Mapped[ProjectVersion] = relationship(back_populates="job_categories")
    catalog_entry: Mapped[JobCategory | None] = relationship(lazy="joined")
    rate_card: Mapped[RateCard | None] = relationship(lazy="joined")


class Contract(Base):
    """Contract document metadata. Bytes live in the storage backend (local disk / S3).

    When a new version is created from an approved one, contract rows are copied
    and share the same `storage_key`; the file is removed from storage only when
    no row references it any more.
    """

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_till: Mapped[date] = mapped_column(Date, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    version: Mapped[ProjectVersion] = relationship(back_populates="contracts")
    uploaded_by: Mapped[User] = relationship(lazy="joined")
