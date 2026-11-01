"""Idempotent seed: roles, rate-card catalog, job categories and (optionally)
local demo users + sample clients.

Demo users are for LOCAL DEVELOPMENT ONLY. Their password defaults to a
documented throwaway value and can be overridden with SEED_DEMO_PASSWORD.
When AUTH_MODE=cognito, users are created without a password hash; create the
matching users (same email) in the Cognito user pool.
"""
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine
from app.models import Client, JobCategory, RateCard, Role, RoleName, User
from app.reference import load_catalog
from app.security.passwords import hash_password

DEMO_USERS = [
    ("crm@example.com", "Priya Sharma", RoleName.CRM),
    ("crm2@example.com", "Arjun Mehta", RoleName.CRM),
    ("approver@example.com", "Rahul Verma", RoleName.APPROVER),
    ("approver2@example.com", "Neha Kapoor", RoleName.APPROVER),
]

DEMO_CLIENTS = [
    {
        "legal_entity_name": "Acme Technologies Pvt Ltd",
        "registered_address": "12 MG Road, Bengaluru, Karnataka 560001",
        "billing_address": "12 MG Road, Bengaluru, Karnataka 560001",
        "mode_of_payment": "Bank Transfer",
        "gst_number": "29ABCDE1234F1Z5",
        "billing_currency": "INR",
        "contact_name": "Kavya Rao",
        "contact_designation": "Procurement Manager",
        "contact_phone": "+91 98450 12345",
        "contact_email": "kavya.rao@acme.example",
    },
    {
        "legal_entity_name": "Globex Corporation",
        "registered_address": "500 Market Street, San Francisco, CA 94105, USA",
        "billing_address": "PO Box 2210, San Francisco, CA 94126, USA",
        "mode_of_payment": "Letter of Credit",
        "gst_number": None,
        "billing_currency": "USD",
        "contact_name": "Daniel Moore",
        "contact_designation": "VP Engineering",
        "contact_phone": "+1 415 555 0134",
        "contact_email": "daniel.moore@globex.example",
    },
]


def seed_reference_data(db: Session) -> None:
    for name in RoleName:
        if not db.scalar(select(Role).where(Role.name == name)):
            db.add(Role(name=name, description={"CRM": "Project creator", "APPROVER": "Project reviewer"}[name]))

    catalog = load_catalog()
    cards: dict[str, RateCard] = {}
    for rc in catalog["rate_cards"]:
        card = db.scalar(select(RateCard).where(RateCard.code == rc["code"])) or RateCard(code=rc["code"])
        card.name, card.currency, card.description, card.is_active = rc["name"], rc["currency"], rc.get("description"), True
        db.add(card)
        cards[rc["code"]] = card
    db.flush()

    for jc in catalog["job_categories"]:
        cat = db.scalar(select(JobCategory).where(JobCategory.name == jc["name"])) or JobCategory(name=jc["name"])
        default = cards.get(jc.get("default_rate_card"))
        cat.default_rate_card_id = default.id if default else None
        cat.is_active = True
        db.add(cat)
    db.flush()


def seed_demo_data(db: Session) -> None:
    settings = get_settings()
    password = os.environ.get("SEED_DEMO_PASSWORD", "Password123!")
    roles = {r.name: r for r in db.scalars(select(Role))}
    first_crm = None
    for email, full_name, role in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                role_id=roles[role].id,
                password_hash=hash_password(password) if settings.auth_mode == "local" else None,
            )
            db.add(user)
        if role == RoleName.CRM and first_crm is None:
            first_crm = user
    db.flush()

    for data in DEMO_CLIENTS:
        if not db.scalar(select(Client).where(Client.legal_entity_name == data["legal_entity_name"])):
            db.add(Client(**data, created_by_id=first_crm.id, updated_by_id=first_crm.id))


def seed(include_demo_users: bool = True) -> None:
    with Session(get_engine()) as db:
        seed_reference_data(db)
        if include_demo_users:
            seed_demo_data(db)
        db.commit()


if __name__ == "__main__":
    seed()
    print("Seed complete.")
