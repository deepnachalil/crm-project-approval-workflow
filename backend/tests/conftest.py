"""Test fixtures. Tests run against in-memory SQLite (no Docker / AWS needed);
the schema is portable and the same code runs on PostgreSQL."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="crm-tests-")
os.environ.update(
    APP_ENV="test",
    DATABASE_URL="sqlite://",
    JWT_SECRET="test-only-secret-not-used-anywhere-else-0123456789",
    AUTH_MODE="local",
    STORAGE_BACKEND="local",
    LOCAL_STORAGE_DIR=os.path.join(_TMP, "storage"),
    PUBLIC_API_URL="http://testserver",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, RateCard, Role, RoleName, User  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402
from app.seed import seed_reference_data  # noqa: E402

PASSWORD = "Password123!"
USERS = {
    "crm": ("crm@example.com", "Priya Sharma", RoleName.CRM),
    "crm2": ("crm2@example.com", "Arjun Mehta", RoleName.CRM),
    "approver": ("approver@example.com", "Rahul Verma", RoleName.APPROVER),
    "approver2": ("approver2@example.com", "Neha Kapoor", RoleName.APPROVER),
}

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@event.listens_for(engine, "connect")
def _sqlite_fk(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


TestingSession = sessionmaker(bind=engine, autoflush=False)


def _override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
_FAST_HASH = hash_password(PASSWORD, iterations=1_000)


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_reference_data(db)
        roles = {r.name: r for r in db.scalars(select(Role))}
        for email, name, role in USERS.values():
            db.add(User(email=email, full_name=name, role_id=roles[role].id, password_hash=_FAST_HASH))
        db.commit()
    yield


@pytest.fixture
def db():
    with TestingSession() as session:
        yield session


@pytest.fixture
def client():
    return TestClient(app)


class Api:
    """Small helper around TestClient with per-role auth headers."""

    def __init__(self, client: TestClient):
        self.client = client
        self._headers: dict[str, dict[str, str]] = {}
        self.user_ids: dict[str, int] = {}

    def headers(self, who: str) -> dict[str, str]:
        if who not in self._headers:
            res = self.client.post("/auth/login", json={"email": USERS[who][0], "password": PASSWORD})
            assert res.status_code == 200, res.text
            self._headers[who] = {"Authorization": f"Bearer {res.json()['access_token']}"}
            self.user_ids[who] = res.json()["user"]["id"]
        return self._headers[who]

    def user_id(self, who: str) -> int:
        self.headers(who)
        return self.user_ids[who]

    def get(self, who, url, **kw):
        return self.client.get(url, headers=self.headers(who), **kw)

    def post(self, who, url, **kw):
        return self.client.post(url, headers=self.headers(who), **kw)

    def put(self, who, url, **kw):
        return self.client.put(url, headers=self.headers(who), **kw)

    def delete(self, who, url, **kw):
        return self.client.delete(url, headers=self.headers(who), **kw)

    # ---- domain helpers ----

    def create_client(self, name: str = "Acme Technologies Pvt Ltd") -> dict:
        res = self.post("crm", "/clients", json=client_payload(name))
        assert res.status_code == 201, res.text
        return res.json()

    def rate_card_ids(self, db) -> list[int]:
        return [rc.id for rc in db.scalars(select(RateCard).order_by(RateCard.id))]

    def create_project(self, db, code: str = "PRJ-001", **overrides) -> dict:
        client_id = overrides.pop("client_id", None) or self.create_client(f"Client for {code}")["id"]
        rc = self.rate_card_ids(db)
        payload = {
            "project_code": code,
            "name": "Payments Platform",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "client_id": client_id,
            "business_unit": "Digital Engineering",
            "approver_id": self.user_id("approver"),
            "job_categories": [
                {"name": "Software Developer", "rate_card_id": rc[0]},
                {"name": "QA Engineer", "rate_card_id": rc[2]},
            ],
        }
        payload.update(overrides)
        res = self.post("crm", "/projects", json=payload)
        assert res.status_code == 201, res.text
        return res.json()

    def upload_contract(self, project_id: int, who: str = "crm", name: str = "msa.pdf", data: bytes = b"%PDF-1.4 test"):
        return self.post(
            who,
            f"/projects/{project_id}/contracts",
            data={"document_type": "Master Services Agreement", "valid_from": "2026-01-01", "valid_till": "2027-01-01"},
            files={"file": (name, data, "application/pdf")},
        )

    def ready_project(self, db, code: str = "PRJ-001", **overrides) -> dict:
        project = self.create_project(db, code, **overrides)
        assert self.upload_contract(project["id"]).status_code == 201
        return project

    def update_payload(self, project_id: int, **overrides) -> dict:
        v = self.get("crm", f"/projects/{project_id}").json()["current_version"]
        payload = {
            "name": v["name"],
            "start_date": v["start_date"],
            "end_date": v["end_date"],
            "client_id": v["client"]["id"] if v["client"] else None,
            "business_unit": v["business_unit"],
            "approver_id": v["approver"]["id"] if v["approver"] else None,
            "job_categories": [
                {"name": jc["name"], "rate_card_id": jc["rate_card"]["id"] if jc["rate_card"] else None}
                for jc in v["job_categories"]
            ],
        }
        payload.update(overrides)
        return payload

    def approved_project(self, db, code: str = "PRJ-001") -> dict:
        project = self.ready_project(db, code)
        assert self.post("crm", f"/projects/{project['id']}/submit", json={}).status_code == 200
        assert self.post("approver", f"/projects/{project['id']}/approve", json={}).status_code == 200
        return project


def client_payload(name: str = "Acme Technologies Pvt Ltd") -> dict:
    return {
        "legal_entity_name": name,
        "registered_address": "12 MG Road, Bengaluru",
        "billing_address": "12 MG Road, Bengaluru",
        "mode_of_payment": "Bank Transfer",
        "gst_number": "29ABCDE1234F1Z5",
        "billing_currency": "INR",
        "primary_contact": {
            "name": "Kavya Rao",
            "designation": "Procurement Manager",
            "phone": "+91 98450 12345",
            "email": "kavya@acme.example",
        },
    }


@pytest.fixture
def api(client):
    return Api(client)
