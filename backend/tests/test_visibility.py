"""Who can see which projects.

* CRM users share one project list (the requirement asks for "Created By" and a "Creator" filter).
* An approver only sees projects that a CRM submitted to them (the approver selected on the project).
"""


def _submitted(api, db, code, approver="approver"):
    project = api.ready_project(db, code, approver_id=api.user_id(approver))
    assert api.post("crm", f"/projects/{project['id']}/submit", json={}).status_code == 200
    return project


def test_approver_only_sees_projects_submitted_to_them(api, db):
    mine = _submitted(api, db, "PRJ-RAHUL")
    theirs = _submitted(api, db, "PRJ-NEHA", approver="approver2")
    draft = api.create_project(db, "PRJ-DRAFT")   # approver chosen, but never submitted

    assert {p["project_code"] for p in api.get("approver", "/projects").json()} == {"PRJ-RAHUL"}
    assert {p["project_code"] for p in api.get("approver2", "/projects").json()} == {"PRJ-NEHA"}
    assert [r["project"]["project_code"] for r in api.get("approver", "/approvals/pending").json()] == ["PRJ-RAHUL"]

    assert api.get("approver", f"/projects/{mine['id']}").status_code == 200
    for project in (theirs, draft):
        pid = project["id"]
        for url in (f"/projects/{pid}", f"/projects/{pid}/versions", f"/projects/{pid}/approvals",
                    f"/projects/{pid}/audit", f"/projects/{pid}/readiness", f"/projects/{pid}/contracts"):
            assert api.get("approver", url).status_code == 404, url


def test_approver_cannot_open_or_decide_another_approvers_request(api, db):
    theirs = _submitted(api, db, "PRJ-NEHA", approver="approver2")
    contract_id = api.get("crm", f"/projects/{theirs['id']}/contracts").json()[0]["id"]

    assert api.get("approver", f"/contracts/{contract_id}").status_code == 404
    assert api.get("approver", f"/contracts/{contract_id}/download-url").status_code == 404
    assert api.post("approver", f"/projects/{theirs['id']}/approve", json={}).status_code == 403
    assert api.post("approver2", f"/projects/{theirs['id']}/approve", json={}).status_code == 200


def test_approver_keeps_access_after_deciding(api, db):
    project = _submitted(api, db, "PRJ-RAHUL")
    assert api.post("approver", f"/projects/{project['id']}/approve", json={}).status_code == 200
    assert api.get("approver", f"/projects/{project['id']}").status_code == 200
    assert {p["project_code"] for p in api.get("approver", "/projects").json()} == {"PRJ-RAHUL"}


def test_all_crm_users_see_all_projects(api, db):
    _submitted(api, db, "PRJ-RAHUL")
    _submitted(api, db, "PRJ-NEHA", approver="approver2")
    api.create_project(db, "PRJ-DRAFT")
    expected = {"PRJ-RAHUL", "PRJ-NEHA", "PRJ-DRAFT"}
    assert {p["project_code"] for p in api.get("crm", "/projects").json()} == expected
    assert {p["project_code"] for p in api.get("crm2", "/projects").json()} == expected
