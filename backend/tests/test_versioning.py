"""Updating an approved project creates a new version that needs approval."""


def _versions(api, project_id):
    return {v["version_number"]: v for v in api.get("crm", f"/projects/{project_id}/versions").json()}


def test_updating_approved_project_creates_new_draft_version(api, db):
    project = api.approved_project(db)
    res = api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="Payments v2"))
    assert res.status_code == 200
    body = res.json()
    assert body["current_version"]["version_number"] == 2
    assert body["current_version"]["status"] == "DRAFT"
    assert body["current_version"]["is_active"] is False
    assert body["current_version"]["based_on_version_number"] == 1
    # Contracts and job categories are carried over.
    assert len(body["current_version"]["contracts"]) == 1
    assert len(body["current_version"]["job_categories"]) == 2


def test_previous_approved_version_remains_unchanged_and_active(api, db):
    project = api.approved_project(db)
    api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="Payments v2"))

    body = api.get("crm", f"/projects/{project['id']}").json()
    assert body["active_version"]["version_number"] == 1
    assert body["active_version"]["name"] == "Payments Platform"
    assert body["active_version"]["status"] == "APPROVED"

    v1 = api.get("crm", f"/projects/{project['id']}/versions/1").json()
    assert v1["name"] == "Payments Platform"
    assert v1["is_active"] is True


def test_further_edits_update_the_same_draft(api, db):
    project = api.approved_project(db)
    api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="v2 a"))
    res = api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="v2 b"))
    assert res.json()["current_version"]["version_number"] == 2
    assert set(_versions(api, project["id"])) == {1, 2}


def test_new_version_requires_approval(api, db):
    project = api.approved_project(db)
    api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="Payments v2"))
    res = api.post("crm", f"/projects/{project['id']}/submit", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "PENDING_APPROVAL"
    assert body["current_version"]["version_number"] == 2
    assert body["active_version"]["version_number"] == 1  # v1 stays in effect meanwhile


def test_new_approved_version_becomes_active(api, db):
    project = api.approved_project(db)
    api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="Payments v2"))
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    res = api.post("approver", f"/projects/{project['id']}/approve", json={})
    assert res.status_code == 200
    assert res.json()["active_version"]["version_number"] == 2

    versions = _versions(api, project["id"])
    assert (versions[1]["status"], versions[1]["is_active"]) == ("APPROVED", False)
    assert (versions[2]["status"], versions[2]["is_active"]) == ("APPROVED", True)


def test_rejected_new_version_keeps_previous_active(api, db):
    project = api.approved_project(db)
    api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="Payments v2"))
    api.post("crm", f"/projects/{project['id']}/submit", json={})
    api.post("approver", f"/projects/{project['id']}/reject", json={"comment": "Not yet"})
    body = api.get("crm", f"/projects/{project['id']}").json()
    assert body["status"] == "REJECTED"
    assert body["active_version"]["version_number"] == 1


def test_version_history_shows_changes(api, db):
    project = api.approved_project(db)
    api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="Payments v2"))
    changes = {c["field"]: c for c in _versions(api, project["id"])[2]["changes"]}
    assert changes["name"]["old"] == "Payments Platform"
    assert changes["name"]["new"] == "Payments v2"


def test_update_without_changes_does_not_create_version(api, db):
    project = api.approved_project(db)
    res = api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"]))
    assert res.status_code == 422
    assert set(_versions(api, project["id"])) == {1}


def test_contract_change_on_approved_project_creates_new_version(api, db):
    project = api.approved_project(db)
    assert api.upload_contract(project["id"], name="sow.pdf").status_code == 201
    body = api.get("crm", f"/projects/{project['id']}").json()
    assert body["current_version"]["version_number"] == 2
    assert len(body["current_version"]["contracts"]) == 2
    assert len(body["active_version"]["contracts"]) == 1


def test_deleting_contract_on_approved_project_only_affects_new_version(api, db):
    project = api.approved_project(db)
    v1_contract = api.get("crm", f"/projects/{project['id']}/contracts").json()[0]
    assert api.delete("crm", f"/contracts/{v1_contract['id']}").status_code == 204

    body = api.get("crm", f"/projects/{project['id']}").json()
    assert body["current_version"]["version_number"] == 2
    assert body["current_version"]["contracts"] == []
    assert len(body["active_version"]["contracts"]) == 1
    # The v1 file is still downloadable since v1 still references it.
    url = api.get("crm", f"/contracts/{v1_contract['id']}/download-url").json()["url"]
    assert api.client.get(url.removeprefix("http://testserver")).status_code == 200
