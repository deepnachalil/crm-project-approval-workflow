from fastapi import APIRouter, status

from app.api.deps import CrmUser, CurrentUserDep, DbSession
from app.repositories import client_repo
from app.schemas.client import ClientIn, ClientOut
from app.services import client_service

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(db: DbSession, _: CurrentUserDep, search: str | None = None) -> list[ClientOut]:
    return [ClientOut.from_model(c) for c in client_repo.list_clients(db, search)]


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: DbSession, _: CurrentUserDep) -> ClientOut:
    return ClientOut.from_model(client_service.get_client(db, client_id))


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(body: ClientIn, db: DbSession, user: CrmUser) -> ClientOut:
    return ClientOut.from_model(client_service.create_client(db, user, body))


@router.put("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, body: ClientIn, db: DbSession, user: CrmUser) -> ClientOut:
    return ClientOut.from_model(client_service.update_client(db, user, client_id, body))
