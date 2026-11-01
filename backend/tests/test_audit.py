def _actions(api, project_id) -> list[str]:
    # API returns newest first; reverse for chronological assertions.
    return [e["action"] for e in reversed(api.get("crm", f"/projects/{project_id}/audit").json())]


def test_full_lifecycle_is_audited(api, db):
    project = api.create_project(db)
    pid = project["id"]
    contract = api.upload_contract(pid).json()
    api.delete("crm", f"/contracts/{contract['id']}")
    api.upload_contract(pid, name="sow.pdf")
    api.put("crm", f"/projects/{pid}", json=api.update_payload(pid, name="Renamed"))
    api.post("crm", f"/projects/{pid}/submit", json={})
    api.post("approver", f"/projects/{pid}/reject", json={"comment": "Fix the name"})
    api.put("crm", f"/projects/{pid}", json=api.update_payload(pid, name="Fixed"))
    api.post("crm", f"/projects/{pid}/resubmit", json={})
    api.post("approver", f"/projects/{pid}/approve", json={})
    api.put("crm", f"/projects/{pid}", json=api.update_payload(pid, name="Version two"))

    assert _actions(api, pid) == [
        "PROJECT_CREATED",
        "CONTRACT_UPLOADED",
        "CONTRACT_DELETED",
        "CONTRACT_UPLOADED",
        "PROJECT_UPDATED",
        "SUBMITTED_FOR_APPROVAL",
        "APPROVAL_ASSIGNED",
        "PROJECT_REJECTED",
        "PROJECT_UPDATED",
        "PROJECT_RESUBMITTED",
        "APPROVAL_ASSIGNED",
        "PROJECT_APPROVED",
        "VERSION_ACTIVATED",
        "NEW_VERSION_CREATED",
        "PROJECT_UPDATED",
    ]


def test_audit_event_contents(api, db):
    project = api.ready_project(db)
    pid = project["id"]
    api.post("crm", f"/projects/{pid}/submit", json={})
    api.post("approver", f"/projects/{pid}/reject", json={"comment": "Missing PO"})

    events = api.get("approver", f"/projects/{pid}/audit").json()
    rejected = next(e for e in events if e["action"] == "PROJECT_REJECTED")
    assert rejected["id"]
    assert rejected["project_id"] == pid
    assert rejected["version_id"] == project["current_version"]["id"]
    assert rejected["version_number"] == 1
    assert rejected["user"]["email"] == "approver@example.com"
    assert rejected["comment"] == "Missing PO"
    assert rejected["created_at"]

    assigned = next(e for e in events if e["action"] == "APPROVAL_ASSIGNED")
    assert assigned["details"]["approver"] == "Rahul Verma"


def test_update_audit_records_field_changes(api, db):
    project = api.create_project(db)
    api.put("crm", f"/projects/{project['id']}", json={**api.update_payload(project["id"], name="New"), "change_note": "rename"})
    event = api.get("crm", f"/projects/{project['id']}/audit").json()[0]
    assert event["action"] == "PROJECT_UPDATED"
    assert event["comment"] == "rename"
    assert event["details"]["changes"][0]["field"] == "name"


def test_failed_actions_are_not_audited(api, db):
    project = api.create_project(db)
    api.post("crm", f"/projects/{project['id']}/submit", json={})  # fails: no contract
    assert _actions(api, project["id"]) == ["PROJECT_CREATED"]
