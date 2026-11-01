"""Submission, approval, rejection and resubmission rules."""


def _fields(res) -> set[str]:
    return {d["field"] for d in res.json()["error"]["details"]}


# ---- submission ---------------------------------------------------------------


def test_cannot_submit_incomplete_project(api):
    project = api.post("crm", "/projects", json={"project_code": "PRJ-1", "name": "Bare"}).json()
    res = api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert res.status_code == 422
    assert {"client_id", "approver_id", "start_date"} <= _fields(res)


def test_cannot_submit_without_contract(api, db):
    project = api.create_project(db)
    res = api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert res.status_code == 422
    assert _fields(res) == {"contracts"}


def test_cannot_submit_without_job_categories(api, db):
    project = api.create_project(db, job_categories=[])
    api.upload_contract(project["id"])
    res = api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert res.status_code == 422
    assert _fields(res) == {"job_categories"}


def test_cannot_submit_without_rate_card_mapping(api, db):
    project = api.create_project(db, job_categories=[{"name": "Software Developer"}])
    api.upload_contract(project["id"])
    res = api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert res.status_code == 422
    assert _fields(res) == {"job_categories[0].rate_card_id"}


def test_valid_submission_moves_to_pending_approval(api, db):
    project = api.ready_project(db)
    res = api.post("crm", f"/projects/{project['id']}/submit", json={"comment": "Please review"})
    assert res.status_code == 200
    assert res.json()["status"] == "PENDING_APPROVAL"

    pending = api.get("approver", "/approvals/pending").json()
    assert [p["project"]["id"] for p in pending] == [project["id"]]
    assert pending[0]["is_resubmission"] is False
    # Only the assigned approver sees it.
    assert api.get("approver2", "/approvals/pending").json() == []


def test_pending_project_cannot_be_edited_or_resubmitted(api, db):
    project = api.ready_project(db)
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"])).status_code == 409
    assert api.upload_contract(project["id"]).status_code == 409
    assert api.post("crm", f"/projects/{project['id']}/submit", json={}).status_code == 409


# ---- approval -----------------------------------------------------------------


def test_approver_can_approve(api, db):
    project = api.ready_project(db)
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert "approve" in api.get("approver", f"/projects/{project['id']}").json()["allowed_actions"]

    res = api.post("approver", f"/projects/{project['id']}/approve", json={"comment": "Looks good"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "APPROVED"
    assert body["active_version"]["version_number"] == 1
    decision = body["current_version"]["last_decision"]
    assert decision["decided_by"]["email"] == "approver@example.com"
    assert decision["decided_at"] is not None
    assert decision["comment"] == "Looks good"

    # CRM sees the updated status.
    assert api.get("crm", f"/projects/{project['id']}").json()["status"] == "APPROVED"


def test_approver_can_reject_with_comment(api, db):
    project = api.ready_project(db)
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    res = api.post("approver", f"/projects/{project['id']}/reject", json={"comment": "Rate card for QA is wrong"})
    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"
    assert res.json()["current_version"]["last_decision"]["comment"] == "Rate card for QA is wrong"


def test_rejection_requires_comments(api, db):
    project = api.ready_project(db)
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    for body in ({}, {"comment": ""}, {"comment": "   "}):
        res = api.post("approver", f"/projects/{project['id']}/reject", json=body)
        assert res.status_code == 422
        assert _fields(res) == {"comment"}
    assert api.get("crm", f"/projects/{project['id']}").json()["status"] == "PENDING_APPROVAL"


def test_crm_cannot_approve_or_reject(api, db):
    project = api.ready_project(db)
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert api.post("crm", f"/projects/{project['id']}/approve", json={}).status_code == 403
    assert api.post("crm", f"/projects/{project['id']}/reject", json={"comment": "x"}).status_code == 403
    assert "approve" not in api.get("crm", f"/projects/{project['id']}").json()["allowed_actions"]


def test_unassigned_approver_cannot_decide(api, db):
    project = api.ready_project(db)
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert api.post("approver2", f"/projects/{project['id']}/approve", json={}).status_code == 403


def test_cannot_approve_a_draft(api, db):
    project = api.ready_project(db)
    assert api.post("approver", f"/projects/{project['id']}/approve", json={}).status_code == 409


def test_approver_cannot_submit(api, db):
    project = api.ready_project(db)
    assert api.post("approver", f"/projects/{project['id']}/submit", json={}).status_code == 403


# ---- rejection / resubmission -------------------------------------------------------


def _rejected_project(api, db) -> dict:
    project = api.ready_project(db)
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    api.post("approver", f"/projects/{project['id']}/reject", json={"comment": "End date too early"})
    return project


def test_crm_can_edit_rejected_project(api, db):
    project = _rejected_project(api, db)
    detail = api.get("crm", f"/projects/{project['id']}").json()
    assert {"edit", "resubmit"} <= set(detail["allowed_actions"])
    assert "submit" not in detail["allowed_actions"]

    res = api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], end_date="2027-06-30"))
    assert res.status_code == 200
    body = res.json()
    # Edited in place: still version 1, still rejected until resubmitted.
    assert body["current_version"]["version_number"] == 1
    assert body["current_version"]["end_date"] == "2027-06-30"
    assert body["status"] == "REJECTED"


def test_crm_can_resubmit_rejected_project(api, db):
    project = _rejected_project(api, db)
    api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], end_date="2027-06-30"))
    assert api.post("crm", f"/projects/{project['id']}/submit", json={}).status_code == 409  # must use resubmit

    res = api.post("crm", f"/projects/{project['id']}/resubmit", json={"comment": "Fixed end date"})
    assert res.status_code == 200
    assert res.json()["status"] == "PENDING_APPROVAL"

    pending = api.get("approver", "/approvals/pending").json()
    assert pending[0]["is_resubmission"] is True

    assert api.post("approver", f"/projects/{project['id']}/approve", json={}).status_code == 200
    history = api.get("crm", f"/projects/{project['id']}/approvals").json()
    assert [h["status"] for h in history] == ["APPROVED", "REJECTED"]
    assert history[1]["comments"][0]["comment"] == "End date too early"


def test_resubmission_is_still_validated(api, db):
    project = _rejected_project(api, db)
    contract_id = api.get("crm", f"/projects/{project['id']}/contracts").json()[0]["id"]
    assert api.delete("crm", f"/contracts/{contract_id}").status_code == 204
    res = api.post("crm", f"/projects/{project['id']}/resubmit", json={})
    assert res.status_code == 422
    assert _fields(res) == {"contracts"}
