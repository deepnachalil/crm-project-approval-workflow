from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import ApprovalRequest, ApprovalStatus


def pending_for_version(db: Session, version_id: int) -> ApprovalRequest | None:
    return db.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.version_id == version_id, ApprovalRequest.status == ApprovalStatus.PENDING
        )
    )


def list_for_project(db: Session, project_id: int) -> list[ApprovalRequest]:
    return list(
        db.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.project_id == project_id)
            .options(selectinload(ApprovalRequest.comments))
            .order_by(ApprovalRequest.submitted_at.desc(), ApprovalRequest.id.desc())
        )
    )


def list_pending_for_approver(db: Session, approver_id: int) -> list[ApprovalRequest]:
    return list(
        db.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.approver_id == approver_id, ApprovalRequest.status == ApprovalStatus.PENDING)
            .order_by(ApprovalRequest.submitted_at)
        )
    )


def latest_by_version(db: Session, version_ids: list[int]) -> dict[int, ApprovalRequest]:
    """Most recent approval request per version."""
    if not version_ids:
        return {}
    rows = db.scalars(
        select(ApprovalRequest)
        .where(ApprovalRequest.version_id.in_(version_ids))
        .options(selectinload(ApprovalRequest.comments))
        .order_by(ApprovalRequest.id)
    )
    return {r.version_id: r for r in rows}  # later rows overwrite earlier ones
