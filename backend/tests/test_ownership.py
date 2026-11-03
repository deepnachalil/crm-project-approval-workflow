"""Only the project's CRM / Creator can change it; other CRM users get read-only access."""


def test_other_crm_can_view_but_not_change(api, db):
    project = api.ready_project(db, "PRJ-PRIYA")      # created by Priya (crm)
    pid = project["id"]

    detail = api.get("crm2", f"/projects/{pid}")
    assert detail.status_code == 200
    assert detail.json()["allowed_actions"] == []
    row = next(p for p in api.get("crm2", "/projects").json() if p["id"] == pid)
    assert row["can_edit"] is False

    contract_id = api.get("crm", f"/projects/{pid}/contracts").json()[0]["id"]
    assert api.put("crm2", f"/projects/{pid}", json=api.update_payload(pid, name="Hijacked")).status_code == 403
    assert api.upload_contract(pid, who="crm2").status_code == 403
    assert api.delete("crm2", f"/contracts/{contract_id}").status_code == 403
    assert api.post("crm2", f"/projects/{pid}/submit", json={}).status_code == 403

    # The owner still has full control.
    assert set(api.get("crm", f"/projects/{pid}").json()["allowed_actions"]) >= {"edit", "submit"}
    assert api.post("crm", f"/projects/{pid}/submit", json={}).status_code == 200


def test_only_owner_can_resubmit_a_rejected_project(api, db):
    project = api.ready_project(db, "PRJ-PRIYA")
    pid = project["id"]
    api.post("crm", f"/projects/{pid}/submit", json={})
    api.post("approver", f"/projects/{pid}/reject", json={"comment": "Fix the dates"})

    assert api.post("crm2", f"/projects/{pid}/resubmit", json={}).status_code == 403
    assert api.post("crm", f"/projects/{pid}/resubmit", json={}).status_code == 200


def test_only_owner_can_update_an_approved_project(api, db):
    project = api.approved_project(db, "PRJ-PRIYA")
    pid = project["id"]
    assert api.put("crm2", f"/projects/{pid}", json=api.update_payload(pid, name="v2 by Arjun")).status_code == 403
    assert api.get("crm", f"/projects/{pid}").json()["current_version"]["version_number"] == 1   # no v2 created
    assert api.put("crm", f"/projects/{pid}", json=api.update_payload(pid, name="v2 by Priya")).status_code == 200


def test_owner_is_the_projects_crm_creator(api, db):
    # Priya creates the project but assigns Arjun as its CRM / Creator: Arjun owns it.
    project = api.create_project(db, "PRJ-ARJUN", crm_user_id=api.user_id("crm2"))
    pid = project["id"]
    assert api.put("crm2", f"/projects/{pid}", json=api.update_payload(pid, name="Arjun edit")).status_code == 200
    assert api.put("crm", f"/projects/{pid}", json=api.update_payload(pid, name="Priya edit")).status_code == 403


def test_created_by_and_creator_filter_show_the_owner(api, db):
    # Priya clicks "New Project" but assigns Arjun as CRM / Creator: the list and filter show Arjun.
    project = api.create_project(db, "PRJ-ARJUN", crm_user_id=api.user_id("crm2"))
    row = next(p for p in api.get("crm", "/projects").json() if p["id"] == project["id"])
    assert row["created_by"]["full_name"] == "Arjun Mehta"
    assert api.get("crm", f"/projects/{project['id']}").json()["created_by"]["full_name"] == "Arjun Mehta"

    by_arjun = api.get("crm", "/projects", params={"created_by": api.user_id("crm2")}).json()
    by_priya = api.get("crm", "/projects", params={"created_by": api.user_id("crm")}).json()
    assert [p["project_code"] for p in by_arjun] == ["PRJ-ARJUN"]
    assert by_priya == []

    # The audit trail still records who actually created it.
    created = api.get("crm", f"/projects/{project['id']}/audit").json()[-1]
    assert created["action"] == "PROJECT_CREATED" and created["user"]["full_name"] == "Priya Sharma"
