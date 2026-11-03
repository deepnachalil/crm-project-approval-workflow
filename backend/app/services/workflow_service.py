"""Approval workflow state transitions.

    Draft            --submit-->    Pending Approval
    Rejected         --resubmit-->  Pending Approval
    Pending Approval --approve-->   Approved (becomes the active version)
    Pending Approval --reject-->    Rejected (comment required)
"""
from sqlalchemy.orm import Session

from app.errors import ConflictError, ValidationFailedError, issue
from app.models import (
    ApprovalComment,
    ApprovalRequest,
    ApprovalStatus,
    AuditAction,
    CommentKind,
    Project,
    RoleName,
    User,
    VersionStatus,
)
from app.models.base import utcnow
from app.repositories import approval_repo
from app.services import audit_service, policies
from app.services.project_service import load_project, touch
from app.services.validation import submission_issues


def _clean(comment: str | None) -> str | None:
    return comment.strip() or None if comment else None


def submit(db: Session, user: User, project_id: int, comment: str | None, *, resubmission: bool = False) -> Project:
    policies.ensure_role(user, RoleName.CRM)
    project = load_project(db, project_id, for_update=True)
    version = project.latest_version

    blocker = policies.owner_blocker(user, version) or policies.submit_blocker(version, resubmission=resubmission)
    if blocker:
        raise blocker
    issues = submission_issues(version)
    if issues:
        raise ValidationFailedError("Project is not ready to be submitted for approval", issues)

    comment = _clean(comment)
    version.status = VersionStatus.PENDING_APPROVAL
    request = ApprovalRequest(
        project_id=project.id,
        version_id=version.id,
        status=ApprovalStatus.PENDING,
        is_resubmission=resubmission,
        submitted_by_id=user.id,
        approver_id=version.approver_id,
    )
    if comment:
        request.comments.append(ApprovalComment(author_id=user.id, kind=CommentKind.SUBMISSION, comment=comment))
    db.add(request)
    touch(project)

    action = AuditAction.PROJECT_RESUBMITTED if resubmission else AuditAction.SUBMITTED_FOR_APPROVAL
    audit_service.record(db, user=user, action=action, version=version, comment=comment)
    audit_service.record(
        db, user=user, action=AuditAction.APPROVAL_ASSIGNED, version=version,
        details={"approver_id": version.approver_id, "approver": version.approver.full_name},
    )
    db.commit()
    return project


def _pending_request(db: Session, version_id: int) -> ApprovalRequest:
    request = approval_repo.pending_for_version(db, version_id)
    if request is None:  # should not happen while status is PENDING_APPROVAL
        raise ConflictError("No pending approval request found for this project")
    return request


def approve(db: Session, user: User, project_id: int, comment: str | None) -> Project:
    project = load_project(db, project_id, for_update=True)
    version = project.latest_version
    blocker = policies.decision_blocker(user, version)
    if blocker:
        raise blocker

    request = _pending_request(db, version.id)
    comment = _clean(comment)
    previous = project.active_version
    if previous is not None:
        previous.is_active = False
        db.flush()  # release the one-active-version unique index before activating the new one

    now = utcnow()
    version.status = VersionStatus.APPROVED
    version.is_active = True
    request.status = ApprovalStatus.APPROVED
    request.decided_by_id = user.id
    request.decided_at = now
    if comment:
        request.comments.append(ApprovalComment(author_id=user.id, kind=CommentKind.APPROVAL, comment=comment))
    touch(project)

    audit_service.record(db, user=user, action=AuditAction.PROJECT_APPROVED, version=version, comment=comment)
    audit_service.record(
        db, user=user, action=AuditAction.VERSION_ACTIVATED, version=version,
        details={"previous_active_version": previous.version_number if previous else None},
    )
    db.commit()
    return project


def reject(db: Session, user: User, project_id: int, comment: str | None) -> Project:
    project = load_project(db, project_id, for_update=True)
    version = project.latest_version
    blocker = policies.decision_blocker(user, version)
    if blocker:
        raise blocker
    comment = _clean(comment)
    if not comment:
        raise ValidationFailedError("Rejection comments are required", [issue("comment", "Provide a rejection reason")])

    request = _pending_request(db, version.id)
    version.status = VersionStatus.REJECTED
    request.status = ApprovalStatus.REJECTED
    request.decided_by_id = user.id
    request.decided_at = utcnow()
    request.comments.append(ApprovalComment(author_id=user.id, kind=CommentKind.REJECTION, comment=comment))
    touch(project)

    audit_service.record(db, user=user, action=AuditAction.PROJECT_REJECTED, version=version, comment=comment)
    db.commit()
    return project
