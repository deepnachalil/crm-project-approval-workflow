"""Single source of truth for workflow/permission rules.

Services call these to *enforce* rules; `allowed_actions` uses the same
predicates so the UI is told exactly what the backend will accept.
"""
from app.errors import AppError, ConflictError, PermissionDeniedError
from app.models import Project, ProjectVersion, RoleName, User, VersionStatus


def ensure_role(user: User, *roles: RoleName) -> None:
    if user.role_name not in roles:
        raise PermissionDeniedError(f"This action requires role: {', '.join(roles)}")


def edit_blocker(latest: ProjectVersion) -> AppError | None:
    """Editing targets the latest version: Draft/Rejected are edited in place,
    Approved spawns a new draft version, Pending Approval is locked."""
    if latest.status == VersionStatus.PENDING_APPROVAL:
        return ConflictError("Project is pending approval and cannot be edited until a decision is made")
    return None


def submit_blocker(latest: ProjectVersion, *, resubmission: bool) -> AppError | None:
    expected = VersionStatus.REJECTED if resubmission else VersionStatus.DRAFT
    if latest.status != expected:
        action = "resubmitted" if resubmission else "submitted"
        return ConflictError(
            f"Only {expected.value.replace('_', ' ').lower()} projects can be {action} "
            f"(current status: {latest.status.value})"
        )
    return None


def decision_blocker(user: User, latest: ProjectVersion) -> AppError | None:
    if user.role_name != RoleName.APPROVER:
        return PermissionDeniedError("Only project approvers can approve or reject projects")
    if latest.status != VersionStatus.PENDING_APPROVAL:
        return ConflictError("Project is not pending approval")
    if latest.approver_id != user.id:
        return PermissionDeniedError("This project is assigned to a different approver")
    return None


def allowed_actions(user: User, project: Project) -> list[str]:
    latest = project.latest_version
    actions: list[str] = []
    if user.role_name == RoleName.CRM:
        if edit_blocker(latest) is None:
            actions += ["edit", "manage_contracts"]
        if submit_blocker(latest, resubmission=False) is None:
            actions.append("submit")
        if submit_blocker(latest, resubmission=True) is None:
            actions.append("resubmit")
    if decision_blocker(user, latest) is None:
        actions += ["approve", "reject"]
    return actions
