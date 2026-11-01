from fastapi import APIRouter

from app.api.deps import ApproverUser, DbSession
from app.repositories import approval_repo, project_repo
from app.schemas.common import UserRef
from app.schemas.project import PendingApprovalOut
from app.services import presenters

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/pending", response_model=list[PendingApprovalOut])
def pending_approvals(db: DbSession, user: ApproverUser) -> list[PendingApprovalOut]:
    """Projects awaiting a decision from the current approver."""
    requests = approval_repo.list_pending_for_approver(db, user.id)
    active = project_repo.active_version_numbers(db, [r.project_id for r in requests])
    result = []
    for r in requests:
        project = r.version.project
        result.append(
            PendingApprovalOut(
                approval_id=r.id,
                project=presenters.project_summary(project, r.version, active.get(project.id), can_edit=False),
                version_number=r.version.version_number,
                is_resubmission=r.is_resubmission,
                submitted_by=UserRef.model_validate(r.submitted_by),
                submitted_at=r.submitted_at,
            )
        )
    return result
