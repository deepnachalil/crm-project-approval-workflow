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


def test_gst_number_is_mandatory_for_every_client(api):
    for country, currency in (("IN", "INR"), ("US", "USD")):
        payload = client_payload(f"No GST {country}")
        payload.update(country=country, billing_currency=currency)
        for missing in (None, "   "):
            payload["gst_number"] = missing
            res = api.post("crm", "/clients", json=payload)
            assert res.status_code == 422
            assert {"field": "gst_number", "message": "GST Number is required"} in res.json()["error"]["details"]


def test_indian_client_needs_a_valid_gstin(api):
    payload = client_payload()
    payload["gst_number"] = "94-3211234"   # a US-style number is not a GSTIN
    res = api.post("crm", "/clients", json=payload)
    assert res.status_code == 422
    assert {"field": "gst_number", "message": "Enter a valid 15-character GSTIN (e.g. 29ABCDE1234F1Z5)"} in (
        res.json()["error"]["details"]
    )
    payload["gst_number"] = " 29abcde1234f1z5 "   # trimmed and upper-cased
    res = api.post("crm", "/clients", json=payload)
    assert res.status_code == 201
    assert res.json()["gst_number"] == "29ABCDE1234F1Z5"


def test_foreign_client_uses_its_tax_registration_number(api):
    payload = client_payload("Globex Corporation")
    payload.update(country="us", gst_number="94-3211234", billing_currency="USD")
    res = api.post("crm", "/clients", json=payload)
    assert res.status_code == 201
    assert res.json()["country"] == "US"
    assert res.json()["gst_number"] == "94-3211234"

    payload.update(legal_entity_name="Bad Tax Id Inc", gst_number="??")
    res = api.post("crm", "/clients", json=payload)
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["message"] == "Enter a valid tax registration number (5-20 letters or digits)"


def test_unsupported_country_rejected(api):
    payload = client_payload()
    payload["country"] = "ZZ"
    res = api.post("crm", "/clients", json=payload)
    assert res.status_code == 422
    assert "country" in {d["field"] for d in res.json()["error"]["details"]}


def test_billing_address_defaults_to_registered_address(api):
    payload = client_payload()
    del payload["billing_address"]
    res = api.post("crm", "/clients", json=payload)
    assert res.status_code == 201
    assert res.json()["billing_address"] == payload["registered_address"]

    payload["billing_address"] = "   "   # blank also means "same as registered"
    res = api.put("crm", f"/clients/{res.json()['id']}", json=payload)
    assert res.status_code == 200
    assert res.json()["billing_address"] == payload["registered_address"]


def test_separate_billing_address_is_kept(api):
    payload = client_payload()
    payload["billing_address"] = "PO Box 2210, Bengaluru"
    res = api.post("crm", "/clients", json=payload)
    assert res.status_code == 201
    assert res.json()["billing_address"] == "PO Box 2210, Bengaluru"


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
