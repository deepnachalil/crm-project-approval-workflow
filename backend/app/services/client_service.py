from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationFailedError, issue
from app.models import AuditAction, Client, RoleName, User
from app.reference import load_catalog
from app.repositories import client_repo
from app.schemas.client import ClientIn
from app.services import audit_service
from app.services.policies import ensure_role


def get_client(db: Session, client_id: int) -> Client:
    client = client_repo.get(db, client_id)
    if client is None:
        raise NotFoundError("Client not found")
    return client


def _validate_reference_values(data: ClientIn) -> None:
    catalog = load_catalog()
    issues = []
    if data.mode_of_payment not in catalog["payment_modes"]:
        issues.append(issue("mode_of_payment", "Unsupported mode of payment"))
    if data.billing_currency not in catalog["currencies"]:
        issues.append(issue("billing_currency", "Unsupported billing currency"))
    if data.country not in {c["code"] for c in catalog["countries"]}:
        issues.append(issue("country", "Unsupported country"))
    if issues:
        raise ValidationFailedError("Invalid client details", issues)


def _apply(client: Client, data: ClientIn, user: User) -> None:
    client.legal_entity_name = data.legal_entity_name
    client.registered_address = data.registered_address
    client.billing_address = data.billing_address
    client.mode_of_payment = data.mode_of_payment
    client.country = data.country
    client.gst_number = data.gst_number
    client.billing_currency = data.billing_currency
    client.contact_name = data.primary_contact.name
    client.contact_designation = data.primary_contact.designation
    client.contact_phone = data.primary_contact.phone
    client.contact_email = data.primary_contact.email
    client.updated_by_id = user.id


def create_client(db: Session, user: User, data: ClientIn) -> Client:
    ensure_role(user, RoleName.CRM)
    _validate_reference_values(data)
    if client_repo.get_by_name(db, data.legal_entity_name):
        raise ConflictError("A client with this legal entity name already exists")
    client = Client(created_by_id=user.id)
    _apply(client, data, user)
    db.add(client)
    db.flush()
    audit_service.record(db, user=user, action=AuditAction.CLIENT_CREATED, client_id=client.id,
                         details={"legal_entity_name": client.legal_entity_name})
    db.commit()
    return client


def update_client(db: Session, user: User, client_id: int, data: ClientIn) -> Client:
    ensure_role(user, RoleName.CRM)
    _validate_reference_values(data)
    client = get_client(db, client_id)
    existing = client_repo.get_by_name(db, data.legal_entity_name)
    if existing and existing.id != client.id:
        raise ConflictError("A client with this legal entity name already exists")
    _apply(client, data, user)
    audit_service.record(db, user=user, action=AuditAction.CLIENT_UPDATED, client_id=client.id,
                         details={"legal_entity_name": client.legal_entity_name})
    db.commit()
    return client
