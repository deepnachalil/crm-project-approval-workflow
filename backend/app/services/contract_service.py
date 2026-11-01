import hashlib
import logging
import re
import uuid
from datetime import date
from pathlib import PurePath

from sqlalchemy.orm import Session

from app.config import ALLOWED_UPLOAD_TYPES, get_settings
from app.errors import ConflictError, NotFoundError, ValidationFailedError, issue
from app.models import AuditAction, Contract, RoleName, User
from app.reference import load_catalog
from app.repositories import project_repo
from app.services import audit_service, policies
from app.services.project_service import editable_version, load_project, touch
from app.storage import get_storage
from app.storage.base import Disposition

log = logging.getLogger(__name__)

# Leading "magic bytes" per extension, so a renamed executable is not accepted as a PDF.
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".docx": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
}


def _safe_file_name(name: str) -> str:
    base = PurePath(name.replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return cleaned[-200:] or "document"


def validate_file(file_name: str, content_type: str | None, data: bytes) -> tuple[str, str]:
    """Return (safe file name, canonical content type) or raise ValidationFailedError."""
    safe_name = _safe_file_name(file_name or "")
    ext = PurePath(safe_name).suffix.lower()
    if ext not in ALLOWED_UPLOAD_TYPES:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_TYPES))
        raise ValidationFailedError("Unsupported file type", [issue("file", f"Allowed file types: {allowed}")])
    canonical_type = next(iter(ALLOWED_UPLOAD_TYPES[ext]))
    if content_type and content_type not in ALLOWED_UPLOAD_TYPES[ext] | {"application/octet-stream"}:
        raise ValidationFailedError("File content type does not match its extension", [issue("file", "Content type mismatch")])
    if not data:
        raise ValidationFailedError("File is empty", [issue("file", "File is empty")])
    max_bytes = get_settings().max_upload_bytes
    if len(data) > max_bytes:
        raise ValidationFailedError("File is too large", [issue("file", f"Maximum size is {max_bytes // (1024 * 1024)} MB")])
    if not data.startswith(_SIGNATURES[ext]):
        raise ValidationFailedError("File content does not match its extension", [issue("file", "File appears to be corrupt or mislabelled")])
    return safe_name, canonical_type


def _validate_metadata(document_type: str, valid_from: date, valid_till: date) -> None:
    issues = []
    if document_type not in load_catalog()["document_types"]:
        issues.append(issue("document_type", "Unsupported document type"))
    if valid_till < valid_from:
        issues.append(issue("valid_till", "Valid till must be on or after valid from"))
    if issues:
        raise ValidationFailedError("Invalid contract details", issues)


def get_contract(db: Session, contract_id: int) -> Contract:
    contract = project_repo.get_contract(db, contract_id)
    if contract is None:
        raise NotFoundError("Contract not found")
    return contract


def list_contracts(db: Session, project_id: int, version_number: int | None = None) -> list[Contract]:
    project = load_project(db, project_id)
    if version_number is None:
        return list(project.latest_version.contracts)
    version = next((v for v in project.versions if v.version_number == version_number), None)
    if version is None:
        raise NotFoundError("Version not found")
    return list(version.contracts)


def upload_contract(
    db: Session,
    user: User,
    project_id: int,
    *,
    document_type: str,
    valid_from: date,
    valid_till: date,
    file_name: str,
    content_type: str | None,
    data: bytes,
) -> Contract:
    policies.ensure_role(user, RoleName.CRM)
    _validate_metadata(document_type, valid_from, valid_till)
    safe_name, canonical_type = validate_file(file_name, content_type, data)

    project = load_project(db, project_id, for_update=True)
    version = editable_version(db, project, user)

    key = f"projects/{project.id}/contracts/{uuid.uuid4().hex}/{safe_name}"
    storage = get_storage()
    storage.save(key, data, canonical_type)
    try:
        contract = Contract(
            document_type=document_type,
            valid_from=valid_from,
            valid_till=valid_till,
            file_name=safe_name,
            content_type=canonical_type,
            size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            storage_key=key,
            uploaded_by_id=user.id,
        )
        version.contracts.append(contract)
        touch(project)
        db.flush()
        audit_service.record(
            db, user=user, action=AuditAction.CONTRACT_UPLOADED, version=version,
            details={"contract_id": contract.id, "file_name": safe_name, "document_type": document_type},
        )
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)  # don't leave orphaned files behind
        raise
    return contract


def delete_contract(db: Session, user: User, contract_id: int) -> None:
    policies.ensure_role(user, RoleName.CRM)
    contract = get_contract(db, contract_id)
    project = load_project(db, contract.version.project_id, for_update=True)
    if contract.version_id != project.latest_version.id:
        raise ConflictError("Contracts on historical versions cannot be modified")

    version = editable_version(db, project, user)
    # If a new draft version was just created, delete that version's copy instead.
    target = next(c for c in version.contracts if c.storage_key == contract.storage_key)
    version.contracts.remove(target)
    touch(project)
    db.flush()
    audit_service.record(
        db, user=user, action=AuditAction.CONTRACT_DELETED, version=version,
        details={"contract_id": target.id, "file_name": target.file_name, "document_type": target.document_type},
    )
    storage_key = target.storage_key
    orphaned = not project_repo.storage_key_in_use(db, storage_key)
    db.commit()
    if orphaned:
        try:
            get_storage().delete(storage_key)
        except Exception:  # the DB is the source of truth; a stray file is harmless
            log.exception("Failed to delete stored file %s", storage_key)


def contract_download_url(db: Session, contract_id: int, disposition: Disposition) -> str:
    contract = get_contract(db, contract_id)
    return get_storage().download_url(contract.storage_key, contract.file_name, contract.content_type, disposition)
