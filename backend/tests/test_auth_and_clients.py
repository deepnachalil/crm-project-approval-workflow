from tests.conftest import PASSWORD, client_payload


def test_login_returns_token_and_role(client):
    res = client.post("/auth/login", json={"email": "CRM@example.com", "password": PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["user"]["role"] == "CRM"


def test_login_rejects_bad_password(client):
    res = client.post("/auth/login", json={"email": "crm@example.com", "password": "wrong"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_protected_endpoints_require_token(client):
    assert client.get("/projects").status_code == 401
    assert client.get("/projects", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me_returns_current_user(api):
    res = api.get("approver", "/auth/me")
    assert res.status_code == 200
    assert res.json()["role"] == "APPROVER"


def test_crm_can_create_and_edit_client(api):
    created = api.create_client()
    assert created["primary_contact"]["email"] == "kavya@acme.example"
    payload = client_payload()
    payload["billing_currency"] = "USD"
    res = api.put("crm", f"/clients/{created['id']}", json=payload)
    assert res.status_code == 200
    assert res.json()["billing_currency"] == "USD"


def test_approver_cannot_create_client(api):
    res = api.post("approver", "/clients", json=client_payload())
    assert res.status_code == 403


def test_client_validation(api):
    payload = client_payload()
    payload["gst_number"] = "NOT-A-GST"
    payload["primary_contact"]["email"] = "bad"
    res = api.post("crm", "/clients", json=payload)
    assert res.status_code == 422
    fields = {d["field"] for d in res.json()["error"]["details"]}
    assert {"gst_number", "primary_contact.email"} <= fields


def test_duplicate_client_name_conflicts(api):
    api.create_client("Globex")
    res = api.post("crm", "/clients", json=client_payload("globex"))
    assert res.status_code == 409


def test_catalog_endpoints(api):
    rate_cards = api.get("crm", "/rate-cards").json()
    assert {"Standard Engineering", "QA Standard", "Management Standard", "Design Standard"} <= {
        r["name"] for r in rate_cards
    }
    categories = api.get("crm", "/job-categories").json()
    dev = next(c for c in categories if c["name"] == "Software Developer")
    assert dev["default_rate_card"]["name"] == "Standard Engineering"
    approvers = api.get("crm", "/users", params={"role": "APPROVER"}).json()
    assert {u["email"] for u in approvers} == {"approver@example.com", "approver2@example.com"}
