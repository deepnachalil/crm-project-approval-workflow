"""Model -> response schema mapping, kept in one place."""
from app.models import ApprovalRequest, ApprovalStatus, AuditEvent, CommentKind, Project, ProjectVersion
from app.schemas.client import ClientOut, ClientRef
from app.schemas.common import UserRef
from app.schemas.project import (
    ApprovalCommentOut,
    ApprovalOut,
    AuditEventOut,
    ContractOut,
    DecisionOut,
    ProjectJobCategoryOut,
    ProjectSummary,
    VersionOut,
)


def decision_out(req: ApprovalRequest | None) -> DecisionOut | None:
    if req is None:
        return None
    kind = {ApprovalStatus.APPROVED: CommentKind.APPROVAL, ApprovalStatus.REJECTED: CommentKind.REJECTION}.get(
        req.status
    )
    return DecisionOut(
        status=req.status,
        submitted_by=UserRef.model_validate(req.submitted_by),
        submitted_at=req.submitted_at,
        approver=UserRef.model_validate(req.approver),
        decided_by=UserRef.model_validate(req.decided_by) if req.decided_by else None,
        decided_at=req.decided_at,
        comment=req.comment_of(kind) if kind else req.comment_of(CommentKind.SUBMISSION),
    )


def version_out(v: ProjectVersion, last_request: ApprovalRequest | None) -> VersionOut:
    return VersionOut(
        id=v.id,
        version_number=v.version_number,
        status=v.status,
        is_active=v.is_active,
        based_on_version_number=v.based_on.version_number if v.based_on else None,
        name=v.name,
        start_date=v.start_date,
        end_date=v.end_date,
        business_unit=v.business_unit,
        client=ClientOut.from_model(v.client) if v.client else None,
        crm_user=UserRef.model_validate(v.crm_user),
        approver=UserRef.model_validate(v.approver) if v.approver else None,
        job_categories=[ProjectJobCategoryOut.model_validate(jc) for jc in v.job_categories],
        contracts=[ContractOut.model_validate(c) for c in v.contracts],
        created_by=UserRef.model_validate(v.created_by),
        created_at=v.created_at,
        updated_at=v.updated_at,
        last_decision=decision_out(last_request),
    )


def project_summary(
    project: Project, latest: ProjectVersion, active_version_number: int | None, can_edit: bool
) -> ProjectSummary:
    return ProjectSummary(
        id=project.id,
        project_code=project.project_code,
        name=latest.name,
        client=ClientRef.model_validate(latest.client) if latest.client else None,
        status=latest.status,
        current_version_number=latest.version_number,
        active_version_number=active_version_number,
        created_by=UserRef.model_validate(project.created_by),
        created_at=project.created_at,
        updated_at=project.updated_at,
        can_edit=can_edit,
    )


def approval_out(req: ApprovalRequest) -> ApprovalOut:
    return ApprovalOut(
        id=req.id,
        version_number=req.version.version_number,
        status=req.status,
        is_resubmission=req.is_resubmission,
        submitted_by=UserRef.model_validate(req.submitted_by),
        submitted_at=req.submitted_at,
        approver=UserRef.model_validate(req.approver),
        decided_by=UserRef.model_validate(req.decided_by) if req.decided_by else None,
        decided_at=req.decided_at,
        comments=[ApprovalCommentOut.model_validate(c) for c in req.comments],
    )


def audit_out(e: AuditEvent) -> AuditEventOut:
    return AuditEventOut(
        id=e.id,
        project_id=e.project_id,
        version_id=e.version_id,
        version_number=e.version.version_number if e.version else None,
        user=UserRef.model_validate(e.user),
        action=e.action,
        comment=e.comment,
        details=e.details,
        created_at=e.created_at,
    )
