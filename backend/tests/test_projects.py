"""Project creation: required fields, client selection, job categories, rate cards."""


def test_create_project_creates_draft_version_1(api, db):
    project = api.create_project(db)
    assert project["status"] == "DRAFT"
    v = project["current_version"]
    assert v["version_number"] == 1
    assert v["is_active"] is False
    assert project["active_version"] is None
    assert v["crm_user"]["email"] == "crm@example.com"
    assert set(project["allowed_actions"]) >= {"edit", "submit"}


def test_create_project_requires_code_and_name(api):
    res = api.post("crm", "/projects", json={"name": "  "})
    assert res.status_code == 422
    fields = {d["field"] for d in res.json()["error"]["details"]}
    assert {"project_code", "name"} <= fields


def test_project_code_must_be_unique(api, db):
    api.create_project(db, "PRJ-001")
    res = api.post("crm", "/projects", json={"project_code": "prj-001", "name": "Other"})
    assert res.status_code == 409


def test_end_date_must_not_precede_start_date(api):
    res = api.post(
        "crm", "/projects",
        json={"project_code": "PRJ-9", "name": "X", "start_date": "2026-05-01", "end_date": "2026-04-01"},
    )
    assert res.status_code == 422


def test_selected_client_details_are_returned(api, db):
    client = api.create_client("Initech Ltd")
    project = api.create_project(db, client_id=client["id"])
    c = project["current_version"]["client"]
    assert c["legal_entity_name"] == "Initech Ltd"
    assert c["gst_number"] == "29ABCDE1234F1Z5"
    assert c["primary_contact"]["designation"] == "Procurement Manager"


def test_unknown_client_is_rejected(api):
    res = api.post("crm", "/projects", json={"project_code": "PRJ-2", "name": "X", "client_id": 9999})
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["field"] == "client_id"


def test_approver_must_have_approver_role(api):
    res = api.post(
        "crm", "/projects", json={"project_code": "PRJ-3", "name": "X", "approver_id": api.user_id("crm2")}
    )
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["field"] == "approver_id"


def test_unknown_rate_card_is_rejected(api):
    res = api.post(
        "crm", "/projects",
        json={"project_code": "PRJ-4", "name": "X", "job_categories": [{"name": "Dev", "rate_card_id": 9999}]},
    )
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["field"] == "job_categories[0].rate_card_id"


def test_duplicate_job_category_names_rejected(api):
    res = api.post(
        "crm", "/projects",
        json={"project_code": "PRJ-5", "name": "X", "job_categories": [{"name": "Dev"}, {"name": "dev"}]},
    )
    assert res.status_code == 422


def test_readiness_reports_missing_contract_job_categories_and_rate_cards(api):
    project = api.post("crm", "/projects", json={"project_code": "PRJ-6", "name": "Bare"}).json()
    issues = api.get("crm", f"/projects/{project['id']}/readiness").json()
    assert issues["ready"] is False
    fields = {i["field"] for i in issues["issues"]}
    assert {"start_date", "end_date", "client_id", "business_unit", "approver_id", "contracts", "job_categories"} <= fields

    api.put("crm", f"/projects/{project['id']}", json={"name": "Bare", "job_categories": [{"name": "Dev"}]})
    fields = {i["field"] for i in api.get("crm", f"/projects/{project['id']}/readiness").json()["issues"]}
    assert "job_categories[0].rate_card_id" in fields
    assert "job_categories" not in fields


def test_approver_cannot_create_or_edit_projects(api, db):
    project = api.create_project(db)
    assert api.post("approver", "/projects", json={"project_code": "X-1", "name": "X"}).status_code == 403
    res = api.put("approver", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="Hack"))
    assert res.status_code == 403
    assert api.upload_contract(project["id"], who="approver").status_code == 403


def test_project_listing_and_filters(api, db):
    a = api.create_project(db, "PRJ-A")
    b = api.ready_project(db, "PRJ-B")
    api.post("crm", f"/projects/{b['id']}/submit", json={})

    rows = api.get("crm", "/projects").json()
    assert {r["project_code"] for r in rows} == {"PRJ-A", "PRJ-B"}
    # Approvers only see what was submitted to them, never other people's drafts.
    assert {r["project_code"] for r in api.get("approver", "/projects").json()} == {"PRJ-B"}
    row = next(r for r in rows if r["project_code"] == "PRJ-B")
    assert row["status"] == "PENDING_APPROVAL"
    assert row["current_version_number"] == 1
    assert row["created_by"]["full_name"] == "Priya Sharma"
    assert row["client"]["legal_entity_name"] == "Client for PRJ-B"

    assert [r["project_code"] for r in api.get("crm", "/projects", params={"status": "DRAFT"}).json()] == ["PRJ-A"]
    client_id = a["current_version"]["client"]["id"]
    assert [r["project_code"] for r in api.get("crm", "/projects", params={"client_id": client_id}).json()] == ["PRJ-A"]
    assert api.get("crm", "/projects", params={"created_by": api.user_id("crm2")}).json() == []
