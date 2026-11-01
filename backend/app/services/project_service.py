"""Project creation, editing and versioning.

Versioning rules
----------------
* Editing always targets the project's *latest* version.
* Draft / Rejected latest version  -> edited in place.
* Pending Approval latest version  -> locked (409).
* Approved latest version          -> a new Draft version N+1 is created as a copy
  (job categories and contract references included) and the edit is applied to
  it. Version N stays Approved and active until N+1 is approved.
"""
from typing import Any

from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationFailedError, issue
from app.models import (
    AuditAction,
    Contract,
    Project,
    ProjectJobCategory,
    ProjectVersion,
    RoleName,
    User,
    VersionStatus,
)
from app.models.base import utcnow
from app.repositories import approval_repo, catalog_repo, client_repo, project_repo, user_repo
from app.schemas.project import (
    FieldChange,
    ProjectCreate,
    ProjectDetail,
    ProjectSummary,
    ProjectUpdate,
    ProjectWrite,
    ReadinessOut,
    VersionOut,
    VersionSummary,
)
from app.schemas.common import UserRef
from app.services import audit_service, policies, presenters
from app.services.validation import submission_issues

# ------------------------------------------------------------------ helpers --


def load_project(db: Session, project_id: int, *, for_update: bool = False) -> Project:
    project = project_repo.get(db, project_id, for_update=for_update)
    if project is None:
        raise NotFoundError("Project not found")
    return project


def touch(project: Project) -> None:
    project.updated_at = utcnow()


def _validate_references(db: Session, data: ProjectWrite) -> None:
    """Check that every referenced row exists and has the right role/state."""
    issues = []
    if data.client_id is not None and client_repo.get(db, data.client_id) is None:
        issues.append(issue("client_id", "Selected client does not exist"))
    if data.crm_user_id is not None:
        crm = user_repo.get(db, data.crm_user_id)
        if crm is None or not crm.is_active or crm.role_name != RoleName.CRM:
            issues.append(issue("crm_user_id", "CRM / creator must be an active CRM user"))
    if data.approver_id is not None:
        approver = user_repo.get(db, data.approver_id)
        if approver is None or not approver.is_active or approver.role_name != RoleName.APPROVER:
            issues.append(issue("approver_id", "Approver must be an active user with the approver role"))
    for i, jc in enumerate(data.job_categories):
        if jc.rate_card_id is not None:
            rc = catalog_repo.get_rate_card(db, jc.rate_card_id)
            if rc is None or not rc.is_active:
                issues.append(issue(f"job_categories[{i}].rate_card_id", "Selected rate card does not exist"))
        if jc.job_category_id is not None and catalog_repo.get_job_category(db, jc.job_category_id) is None:
            issues.append(issue(f"job_categories[{i}].job_category_id", "Unknown catalog job category"))
    if issues:
        raise ValidationFailedError("Invalid project details", issues)


def _apply(version: ProjectVersion, data: ProjectWrite) -> None:
    version.name = data.name
    version.start_date = data.start_date
    version.end_date = data.end_date
    version.business_unit = data.business_unit
    version.client_id = data.client_id
    if data.crm_user_id is not None:
        version.crm_user_id = data.crm_user_id
    version.approver_id = data.approver_id
    version.job_categories = [
        ProjectJobCategory(position=i, name=jc.name, job_category_id=jc.job_category_id, rate_card_id=jc.rate_card_id)
        for i, jc in enumerate(data.job_categories)
    ]


def _refresh(db: Session, version: ProjectVersion) -> None:
    """Flush and reload relationships so snapshots/validation see current rows."""
    db.flush()
    db.refresh(version)


# --------------------------------------------------------- snapshot / diff --

_LABELS = {
    "name": "Project Name",
    "start_date": "Start Date",
    "end_date": "End Date",
    "business_unit": "Business Unit",
    "client": "Client",
    "crm_user": "CRM / Creator",
    "approver": "Reviewer / Approver",
    "job_categories": "Job Categories & Rate Cards",
    "contracts": "Contracts",
}


def snapshot(v: ProjectVersion) -> dict[str, Any]:
    """Comparable, human-readable view of a version's configuration."""
    return {
        "name": v.name,
        "start_date": v.start_date.isoformat() if v.start_date else None,
        "end_date": v.end_date.isoformat() if v.end_date else None,
        "business_unit": v.business_unit,
        "client": v.client.legal_entity_name if v.client else None,
        "crm_user": v.crm_user.full_name if v.crm_user else None,
        "approver": v.approver.full_name if v.approver else None,
        "job_categories": [
            f"{jc.name} → {jc.rate_card.name if jc.rate_card else '(no rate card)'}" for jc in v.job_categories
        ],
        "contracts": [
            f"{c.document_type}: {c.file_name} ({c.valid_from.isoformat()} – {c.valid_till.isoformat()})"
            for c in v.contracts
        ],
    }


def diff(old: dict[str, Any] | None, new: dict[str, Any]) -> list[FieldChange]:
    if old is None:
        return []
    return [
        FieldChange(field=k, label=_LABELS[k], old=old.get(k), new=new[k])
        for k in new
        if old.get(k) != new[k]
    ]


# ------------------------------------------------------------- versioning --


def _new_version_from(db: Session, project: Project, source: ProjectVersion, user: User) -> ProjectVersion:
    new = ProjectVersion(
        version_number=project.latest_version_number + 1,
        status=VersionStatus.DRAFT,
        is_active=False,
        based_on_version_id=source.id,
        name=source.name,
        start_date=source.start_date,
        end_date=source.end_date,
        business_unit=source.business_unit,
        client_id=source.client_id,
        crm_user_id=source.crm_user_id,
        approver_id=source.approver_id,
        created_by_id=user.id,
        job_categories=[
            ProjectJobCategory(
                position=jc.position, name=jc.name, job_category_id=jc.job_category_id, rate_card_id=jc.rate_card_id
            )
            for jc in source.job_categories
        ],
        contracts=[
            Contract(
                document_type=c.document_type,
                valid_from=c.valid_from,
                valid_till=c.valid_till,
                file_name=c.file_name,
                content_type=c.content_type,
                size_bytes=c.size_bytes,
                checksum_sha256=c.checksum_sha256,
                storage_key=c.storage_key,  # shared reference, no file copy
                uploaded_by_id=c.uploaded_by_id,
                uploaded_at=c.uploaded_at,
            )
            for c in source.contracts
        ],
    )
    project.versions.append(new)
    project.latest_version_number = new.version_number
    _refresh(db, new)
    audit_service.record(
        db,
        user=user,
        action=AuditAction.NEW_VERSION_CREATED,
        version=new,
        details={"based_on_version": source.version_number},
    )
    return new


def editable_version(db: Session, project: Project, user: User) -> ProjectVersion:
    """Return the version that edits should be applied to (creating one if needed)."""
    latest = project.latest_version
    blocker = policies.edit_blocker(latest)
    if blocker:
        raise blocker
    if latest.status == VersionStatus.APPROVED:
        return _new_version_from(db, project, latest, user)
    return latest


# ------------------------------------------------------------------ commands --


def create_project(db: Session, user: User, data: ProjectCreate) -> Project:
    policies.ensure_role(user, RoleName.CRM)
    if project_repo.get_by_code(db, data.project_code):
        raise ConflictError(f"Project ID '{data.project_code}' is already in use")
    _validate_references(db, data)

    project = Project(project_code=data.project_code, created_by_id=user.id, latest_version_number=1)
    version = ProjectVersion(version_number=1, status=VersionStatus.DRAFT, crm_user_id=user.id, created_by_id=user.id)
    _apply(version, data)
    project.versions.append(version)
    db.add(project)
    _refresh(db, version)
    audit_service.record(
        db, user=user, action=AuditAction.PROJECT_CREATED, version=version,
        details={"project_code": project.project_code, "name": version.name},
    )
    db.commit()
    return project


def update_project(db: Session, user: User, project_id: int, data: ProjectUpdate) -> Project:
    policies.ensure_role(user, RoleName.CRM)
    _validate_references(db, data)
    project = load_project(db, project_id, for_update=True)
    source_status = project.latest_version.status

    version = editable_version(db, project, user)
    before = snapshot(version)
    _apply(version, data)
    _refresh(db, version)
    changes = diff(before, snapshot(version))

    if not changes and source_status == VersionStatus.APPROVED:
        db.rollback()  # discard the speculative new version
        raise ValidationFailedError("No changes detected; the approved version was left unchanged")

    touch(project)
    audit_service.record(
        db, user=user, action=AuditAction.PROJECT_UPDATED, version=version, comment=data.change_note,
        details={"changes": [c.model_dump() for c in changes]},
    )
    db.commit()
    return project


# ------------------------------------------------------------------ queries --


def can_edit(user: User, latest: ProjectVersion) -> bool:
    return user.role_name == RoleName.CRM and policies.edit_blocker(latest) is None


def list_projects(
    db: Session,
    user: User,
    *,
    status: VersionStatus | None = None,
    client_id: int | None = None,
    created_by_id: int | None = None,
    search: str | None = None,
) -> list[ProjectSummary]:
    rows = project_repo.list_projects(
        db, status=status, client_id=client_id, created_by_id=created_by_id, search=search
    )
    active = project_repo.active_version_numbers(db, [p.id for p, _ in rows])
    return [presenters.project_summary(p, v, active.get(p.id), can_edit(user, v)) for p, v in rows]


def project_detail(db: Session, user: User, project_id: int) -> ProjectDetail:
    project = load_project(db, project_id)
    latest, active = project.latest_version, project.active_version
    decisions = approval_repo.latest_by_version(db, [v.id for v in (latest, active) if v])
    return ProjectDetail(
        id=project.id,
        project_code=project.project_code,
        status=latest.status,
        created_by=UserRef.model_validate(project.created_by),
        created_at=project.created_at,
        updated_at=project.updated_at,
        current_version=presenters.version_out(latest, decisions.get(latest.id)),
        active_version=presenters.version_out(active, decisions.get(active.id)) if active else None,
        allowed_actions=policies.allowed_actions(user, project),
    )


def version_history(db: Session, project_id: int) -> list[VersionSummary]:
    project = load_project(db, project_id)
    decisions = approval_repo.latest_by_version(db, [v.id for v in project.versions])
    by_id = {v.id: v for v in project.versions}
    result = []
    for v in sorted(project.versions, key=lambda x: x.version_number, reverse=True):
        base = by_id.get(v.based_on_version_id) if v.based_on_version_id else None
        result.append(
            VersionSummary(
                id=v.id,
                version_number=v.version_number,
                status=v.status,
                is_active=v.is_active,
                based_on_version_number=base.version_number if base else None,
                created_by=UserRef.model_validate(v.created_by),
                created_at=v.created_at,
                updated_at=v.updated_at,
                last_decision=presenters.decision_out(decisions.get(v.id)),
                changes=diff(snapshot(base) if base else None, snapshot(v)),
            )
        )
    return result


def get_version(db: Session, project_id: int, version_number: int) -> VersionOut:
    project = load_project(db, project_id)
    version = next((v for v in project.versions if v.version_number == version_number), None)
    if version is None:
        raise NotFoundError("Version not found")
    return presenters.version_out(version, approval_repo.latest_by_version(db, [version.id]).get(version.id))


def readiness(db: Session, project_id: int) -> ReadinessOut:
    project = load_project(db, project_id)
    issues = submission_issues(project.latest_version)
    return ReadinessOut(ready=not issues, issues=issues)
