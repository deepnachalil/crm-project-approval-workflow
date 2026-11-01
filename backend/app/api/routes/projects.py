from fastapi import APIRouter, status

from app.api.deps import ApproverUser, CrmUser, CurrentUserDep, DbSession
from app.models import VersionStatus
from app.repositories import approval_repo, audit_repo
from app.schemas.project import (
    ApprovalOut,
    AuditEventOut,
    DecisionIn,
    ProjectCreate,
    ProjectDetail,
    ProjectSummary,
    ProjectUpdate,
    ReadinessOut,
    SubmitIn,
    VersionOut,
    VersionSummary,
)
from app.services import presenters, project_service, workflow_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
def list_projects(
    db: DbSession,
    user: CurrentUserDep,
    status: VersionStatus | None = None,
    client_id: int | None = None,
    created_by: int | None = None,
    search: str | None = None,
) -> list[ProjectSummary]:
    return project_service.list_projects(
        db, user, status=status, client_id=client_id, created_by_id=created_by, search=search
    )


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: DbSession, user: CrmUser) -> ProjectDetail:
    project = project_service.create_project(db, user, body)
    return project_service.project_detail(db, user, project.id)


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: DbSession, user: CurrentUserDep) -> ProjectDetail:
    return project_service.project_detail(db, user, project_id)


@router.put("/{project_id}", response_model=ProjectDetail)
def update_project(project_id: int, body: ProjectUpdate, db: DbSession, user: CrmUser) -> ProjectDetail:
    project_service.update_project(db, user, project_id, body)
    return project_service.project_detail(db, user, project_id)


@router.get("/{project_id}/readiness", response_model=ReadinessOut)
def readiness(project_id: int, db: DbSession, _: CurrentUserDep) -> ReadinessOut:
    return project_service.readiness(db, project_id)


@router.get("/{project_id}/versions", response_model=list[VersionSummary])
def list_versions(project_id: int, db: DbSession, _: CurrentUserDep) -> list[VersionSummary]:
    return project_service.version_history(db, project_id)


@router.get("/{project_id}/versions/{version_number}", response_model=VersionOut)
def get_version(project_id: int, version_number: int, db: DbSession, _: CurrentUserDep) -> VersionOut:
    return project_service.get_version(db, project_id, version_number)


@router.get("/{project_id}/approvals", response_model=list[ApprovalOut])
def approval_history(project_id: int, db: DbSession, _: CurrentUserDep) -> list[ApprovalOut]:
    project_service.load_project(db, project_id)
    return [presenters.approval_out(r) for r in approval_repo.list_for_project(db, project_id)]


@router.get("/{project_id}/audit", response_model=list[AuditEventOut])
def audit_trail(project_id: int, db: DbSession, _: CurrentUserDep) -> list[AuditEventOut]:
    project_service.load_project(db, project_id)
    return [presenters.audit_out(e) for e in audit_repo.list_for_project(db, project_id)]


# ----------------------------------------------------------------- workflow --


@router.post("/{project_id}/submit", response_model=ProjectDetail)
def submit(project_id: int, db: DbSession, user: CrmUser, body: SubmitIn | None = None) -> ProjectDetail:
    workflow_service.submit(db, user, project_id, body.comment if body else None)
    return project_service.project_detail(db, user, project_id)


@router.post("/{project_id}/resubmit", response_model=ProjectDetail)
def resubmit(project_id: int, db: DbSession, user: CrmUser, body: SubmitIn | None = None) -> ProjectDetail:
    workflow_service.submit(db, user, project_id, body.comment if body else None, resubmission=True)
    return project_service.project_detail(db, user, project_id)


@router.post("/{project_id}/approve", response_model=ProjectDetail)
def approve(project_id: int, db: DbSession, user: ApproverUser, body: DecisionIn | None = None) -> ProjectDetail:
    workflow_service.approve(db, user, project_id, body.comment if body else None)
    return project_service.project_detail(db, user, project_id)


@router.post("/{project_id}/reject", response_model=ProjectDetail)
def reject(project_id: int, body: DecisionIn, db: DbSession, user: ApproverUser) -> ProjectDetail:
    workflow_service.reject(db, user, project_id, body.comment)
    return project_service.project_detail(db, user, project_id)
