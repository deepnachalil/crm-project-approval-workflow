from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import ApprovalRequest, Contract, Project, ProjectVersion, VersionStatus


def get(db: Session, project_id: int, *, for_update: bool = False) -> Project | None:
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.versions).selectinload(ProjectVersion.job_categories),
            selectinload(Project.versions).selectinload(ProjectVersion.contracts),
        )
    )
    if for_update:
        # Serialises concurrent workflow transitions on the same project (no-op on SQLite).
        stmt = stmt.with_for_update(of=Project)
    return db.scalar(stmt)


def get_by_code(db: Session, project_code: str) -> Project | None:
    return db.scalar(select(Project).where(func.upper(Project.project_code) == project_code.upper()))


def list_projects(
    db: Session,
    *,
    status: VersionStatus | None = None,
    client_id: int | None = None,
    created_by_id: int | None = None,
    search: str | None = None,
    submitted_to_id: int | None = None,
) -> list[tuple[Project, ProjectVersion]]:
    """Projects joined to their latest version (which drives the listed status).

    `submitted_to_id` limits the list to projects that were ever submitted to that approver.
    """
    stmt = (
        select(Project, ProjectVersion)
        .join(
            ProjectVersion,
            and_(
                ProjectVersion.project_id == Project.id,
                ProjectVersion.version_number == Project.latest_version_number,
            ),
        )
        .order_by(Project.updated_at.desc())
    )
    if status:
        stmt = stmt.where(ProjectVersion.status == status)
    if client_id:
        stmt = stmt.where(ProjectVersion.client_id == client_id)
    if created_by_id:   # "Creator" filter: the CRM / Creator of the latest version (the project owner)
        stmt = stmt.where(ProjectVersion.crm_user_id == created_by_id)
    if submitted_to_id:
        stmt = stmt.where(
            exists().where(ApprovalRequest.project_id == Project.id, ApprovalRequest.approver_id == submitted_to_id)
        )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Project.project_code.ilike(pattern) | ProjectVersion.name.ilike(pattern))
    return [(row[0], row[1]) for row in db.execute(stmt)]


def active_version_numbers(db: Session, project_ids: list[int]) -> dict[int, int]:
    if not project_ids:
        return {}
    rows = db.execute(
        select(ProjectVersion.project_id, ProjectVersion.version_number).where(
            ProjectVersion.project_id.in_(project_ids), ProjectVersion.is_active.is_(True)
        )
    )
    return {pid: num for pid, num in rows}


def get_contract(db: Session, contract_id: int) -> Contract | None:
    return db.get(Contract, contract_id)


def storage_key_in_use(db: Session, storage_key: str) -> bool:
    return db.scalar(select(func.count()).select_from(Contract).where(Contract.storage_key == storage_key)) > 0
