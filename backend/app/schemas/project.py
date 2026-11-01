from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.models.enums import ApprovalStatus, AuditAction, CommentKind, VersionStatus
from app.schemas.catalog import RateCardOut
from app.schemas.client import ClientOut, ClientRef
from app.schemas.common import NonEmptyStr, NormalizedUpper, ORMModel, UserRef

ProjectCode = Annotated[str, NormalizedUpper, StringConstraints(pattern=r"^[A-Z0-9][A-Z0-9_-]{2,31}$")]


# ---------------------------------------------------------------- input ----


class JobCategoryIn(BaseModel):
    name: NonEmptyStr = Field(max_length=255)
    job_category_id: int | None = None
    rate_card_id: int | None = None


class ProjectWrite(BaseModel):
    """Fields shared by create and update. Drafts may be saved partially;
    completeness is enforced at submission time (see services/validation.py)."""

    name: NonEmptyStr = Field(max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    client_id: int | None = None
    business_unit: str | None = Field(default=None, max_length=128)
    crm_user_id: int | None = None
    approver_id: int | None = None
    job_categories: list[JobCategoryIn] = Field(default_factory=list, max_length=50)

    @field_validator("business_unit")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None

    @model_validator(mode="after")
    def _check(self) -> "ProjectWrite":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Project end date must be on or after the start date")
        names = [jc.name.lower() for jc in self.job_categories]
        if len(names) != len(set(names)):
            raise ValueError("Job category names must be unique within a project")
        return self


class ProjectCreate(ProjectWrite):
    project_code: ProjectCode


class ProjectUpdate(ProjectWrite):
    change_note: str | None = Field(default=None, max_length=2000)


class SubmitIn(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class DecisionIn(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


# --------------------------------------------------------------- output ----


class ContractOut(ORMModel):
    id: int
    version_id: int
    document_type: str
    valid_from: date
    valid_till: date
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by: UserRef
    uploaded_at: datetime


class ProjectJobCategoryOut(ORMModel):
    id: int
    name: str
    job_category_id: int | None
    rate_card: RateCardOut | None


class DecisionOut(BaseModel):
    status: ApprovalStatus
    submitted_by: UserRef
    submitted_at: datetime
    approver: UserRef
    decided_by: UserRef | None
    decided_at: datetime | None
    comment: str | None


class VersionOut(BaseModel):
    id: int
    version_number: int
    status: VersionStatus
    is_active: bool
    based_on_version_number: int | None
    name: str
    start_date: date | None
    end_date: date | None
    business_unit: str | None
    client: ClientOut | None
    crm_user: UserRef
    approver: UserRef | None
    job_categories: list[ProjectJobCategoryOut]
    contracts: list[ContractOut]
    created_by: UserRef
    created_at: datetime
    updated_at: datetime
    last_decision: DecisionOut | None


class FieldChange(BaseModel):
    field: str
    label: str
    old: Any
    new: Any


class VersionSummary(BaseModel):
    id: int
    version_number: int
    status: VersionStatus
    is_active: bool
    based_on_version_number: int | None
    created_by: UserRef
    created_at: datetime
    updated_at: datetime
    last_decision: DecisionOut | None
    changes: list[FieldChange]


class ProjectSummary(BaseModel):
    id: int
    project_code: str
    name: str
    client: ClientRef | None
    status: VersionStatus
    current_version_number: int
    active_version_number: int | None
    created_by: UserRef
    created_at: datetime
    updated_at: datetime
    can_edit: bool


class ProjectDetail(BaseModel):
    id: int
    project_code: str
    status: VersionStatus
    created_by: UserRef
    created_at: datetime
    updated_at: datetime
    current_version: VersionOut
    active_version: VersionOut | None
    allowed_actions: list[str]


class ReadinessOut(BaseModel):
    ready: bool
    issues: list[dict[str, str]]


class ApprovalCommentOut(ORMModel):
    id: int
    kind: CommentKind
    comment: str
    author: UserRef
    created_at: datetime


class ApprovalOut(BaseModel):
    id: int
    version_number: int
    status: ApprovalStatus
    is_resubmission: bool
    submitted_by: UserRef
    submitted_at: datetime
    approver: UserRef
    decided_by: UserRef | None
    decided_at: datetime | None
    comments: list[ApprovalCommentOut]


class PendingApprovalOut(BaseModel):
    approval_id: int
    project: ProjectSummary
    version_number: int
    is_resubmission: bool
    submitted_by: UserRef
    submitted_at: datetime


class AuditEventOut(BaseModel):
    id: int
    project_id: int | None
    version_id: int | None
    version_number: int | None
    user: UserRef
    action: AuditAction
    comment: str | None
    details: dict[str, Any] | None
    created_at: datetime
