"""Submission readiness rules: a project version may only go to approval when
every mandatory field is set, at least one contract is attached and every job
category is mapped to a rate card."""
from app.errors import issue
from app.models import ProjectVersion, RoleName


def submission_issues(version: ProjectVersion) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    if not version.name or not version.name.strip():
        issues.append(issue("name", "Project name is required"))
    if version.start_date is None:
        issues.append(issue("start_date", "Project start date is required"))
    if version.end_date is None:
        issues.append(issue("end_date", "Project end date is required"))
    if version.start_date and version.end_date and version.end_date < version.start_date:
        issues.append(issue("end_date", "Project end date must be on or after the start date"))
    if not version.business_unit:
        issues.append(issue("business_unit", "Business unit is required"))
    if version.client_id is None:
        issues.append(issue("client_id", "Select a client"))
    if version.crm_user_id is None:
        issues.append(issue("crm_user_id", "CRM / creator is required"))
    if version.approver_id is None:
        issues.append(issue("approver_id", "Select a project approver"))
    elif version.approver is not None and version.approver.role_name != RoleName.APPROVER:
        issues.append(issue("approver_id", "Selected approver does not have the approver role"))

    if not version.contracts:
        issues.append(issue("contracts", "Upload at least one contract document"))

    if not version.job_categories:
        issues.append(issue("job_categories", "Define at least one job category"))
    for i, jc in enumerate(version.job_categories):
        if jc.rate_card_id is None:
            issues.append(issue(f"job_categories[{i}].rate_card_id", f"Map a rate card for job category '{jc.name}'"))

    return issues
