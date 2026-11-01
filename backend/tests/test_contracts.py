def test_upload_list_view_and_download(api, db):
    project = api.create_project(db)
    res = api.upload_contract(project["id"], name="Master Agreement.pdf", data=b"%PDF-1.7 hello")
    assert res.status_code == 201
    contract = res.json()
    assert contract["file_name"] == "Master Agreement.pdf"
    assert contract["content_type"] == "application/pdf"

    assert [c["id"] for c in api.get("crm", f"/projects/{project['id']}/contracts").json()] == [contract["id"]]
    assert api.get("approver", f"/contracts/{contract['id']}").json()["document_type"] == "Master Services Agreement"

    url = api.get("approver", f"/contracts/{contract['id']}/download-url", params={"disposition": "inline"}).json()["url"]
    file_res = api.client.get(url.removeprefix("http://testserver"))
    assert file_res.status_code == 200
    assert file_res.content == b"%PDF-1.7 hello"
    assert file_res.headers["content-disposition"].startswith("inline")


def test_download_token_is_required(client):
    assert client.get("/files/not-a-token").status_code == 401


def test_rejects_unsupported_file_type(api, db):
    project = api.create_project(db)
    res = api.upload_contract(project["id"], name="evil.exe", data=b"MZ...")
    assert res.status_code == 422


def test_rejects_mislabelled_file(api, db):
    project = api.create_project(db)
    res = api.upload_contract(project["id"], name="fake.pdf", data=b"MZ not really a pdf")
    assert res.status_code == 422


def test_rejects_empty_file(api, db):
    project = api.create_project(db)
    assert api.upload_contract(project["id"], data=b"").status_code == 422


def test_rejects_invalid_validity_dates(api, db):
    project = api.create_project(db)
    res = api.post(
        "crm", f"/projects/{project['id']}/contracts",
        data={"document_type": "Statement of Work", "valid_from": "2026-05-01", "valid_till": "2026-01-01"},
        files={"file": ("sow.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["field"] == "valid_till"


def test_rejects_unknown_document_type(api, db):
    project = api.create_project(db)
    res = api.post(
        "crm", f"/projects/{project['id']}/contracts",
        data={"document_type": "Napkin", "valid_from": "2026-01-01", "valid_till": "2026-02-01"},
        files={"file": ("sow.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert res.status_code == 422


def test_delete_contract_from_draft(api, db):
    project = api.create_project(db)
    contract = api.upload_contract(project["id"]).json()
    assert api.delete("crm", f"/contracts/{contract['id']}").status_code == 204
    assert api.get("crm", f"/projects/{project['id']}/contracts").json() == []
    assert api.get("crm", f"/contracts/{contract['id']}").status_code == 404


def test_cannot_delete_contract_of_historical_version(api, db):
    project = api.approved_project(db)
    v1_contract = api.get("crm", f"/projects/{project['id']}/contracts").json()[0]
    # Creates version 2 (a copy of v1's contracts).
    api.put("crm", f"/projects/{project['id']}", json=api.update_payload(project["id"], name="v2"))
    res = api.delete("crm", f"/contracts/{v1_contract['id']}")
    assert res.status_code == 409
