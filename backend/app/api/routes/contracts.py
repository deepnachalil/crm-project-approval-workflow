from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Response, UploadFile, status
from pydantic import BaseModel

from app.api.deps import CrmUser, CurrentUserDep, DbSession
from app.config import get_settings
from app.errors import ValidationFailedError, issue
from app.schemas.project import ContractOut
from app.services import contract_service, project_service

router = APIRouter(tags=["contracts"])


class DownloadUrlOut(BaseModel):
    url: str
    expires_in: int


@router.get("/projects/{project_id}/contracts", response_model=list[ContractOut])
def list_contracts(
    project_id: int, db: DbSession, user: CurrentUserDep, version: int | None = None
) -> list[ContractOut]:
    project_service.ensure_can_view(db, user, project_id)
    return [ContractOut.model_validate(c) for c in contract_service.list_contracts(db, project_id, version)]


@router.post("/projects/{project_id}/contracts", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def upload_contract(
    project_id: int,
    db: DbSession,
    user: CrmUser,
    document_type: Annotated[str, Form()],
    valid_from: Annotated[date, Form()],
    valid_till: Annotated[date, Form()],
    file: Annotated[UploadFile, File()],
) -> ContractOut:
    # Read at most one byte over the limit so oversized uploads are rejected without buffering everything.
    max_bytes = get_settings().max_upload_bytes
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValidationFailedError("File is too large", [issue("file", f"Maximum size is {get_settings().max_upload_mb} MB")])
    contract = contract_service.upload_contract(
        db,
        user,
        project_id,
        document_type=document_type.strip(),
        valid_from=valid_from,
        valid_till=valid_till,
        file_name=file.filename or "",
        content_type=file.content_type,
        data=data,
    )
    return ContractOut.model_validate(contract)


@router.get("/contracts/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: int, db: DbSession, user: CurrentUserDep) -> ContractOut:
    contract = contract_service.get_contract(db, contract_id)
    project_service.ensure_can_view(db, user, contract.version.project_id)
    return ContractOut.model_validate(contract)


@router.get("/contracts/{contract_id}/download-url", response_model=DownloadUrlOut)
def contract_download_url(
    contract_id: int,
    db: DbSession,
    user: CurrentUserDep,
    disposition: Literal["inline", "attachment"] = "attachment",
) -> DownloadUrlOut:
    """Short-lived URL (S3 presigned URL on AWS, signed local link in development)."""
    contract = contract_service.get_contract(db, contract_id)
    project_service.ensure_can_view(db, user, contract.version.project_id)
    url = contract_service.contract_download_url(db, contract_id, disposition)
    return DownloadUrlOut(url=url, expires_in=get_settings().download_url_expires_seconds)


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: int, db: DbSession, user: CrmUser) -> Response:
    contract_service.delete_contract(db, user, contract_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
