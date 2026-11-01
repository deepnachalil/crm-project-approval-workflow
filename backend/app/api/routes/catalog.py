from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DbSession
from app.config import ALLOWED_UPLOAD_TYPES, get_settings
from app.models import RoleName
from app.reference import load_catalog
from app.repositories import catalog_repo, user_repo
from app.schemas.catalog import JobCategoryOut, MetaOut, RateCardOut
from app.schemas.common import UserRef

router = APIRouter(tags=["catalog"])


@router.get("/rate-cards", response_model=list[RateCardOut])
def list_rate_cards(db: DbSession, _: CurrentUserDep) -> list[RateCardOut]:
    return [RateCardOut.model_validate(r) for r in catalog_repo.list_rate_cards(db)]


@router.get("/job-categories", response_model=list[JobCategoryOut])
def list_job_categories(db: DbSession, _: CurrentUserDep) -> list[JobCategoryOut]:
    return [JobCategoryOut.model_validate(j) for j in catalog_repo.list_job_categories(db)]


@router.get("/users", response_model=list[UserRef])
def list_users(db: DbSession, _: CurrentUserDep, role: RoleName | None = None) -> list[UserRef]:
    """Used to populate CRM / approver pickers."""
    return [UserRef.model_validate(u) for u in user_repo.list_users(db, role)]


@router.get("/meta", response_model=MetaOut)
def meta(_: CurrentUserDep) -> MetaOut:
    catalog = load_catalog()
    settings = get_settings()
    return MetaOut(
        business_units=catalog["business_units"],
        payment_modes=catalog["payment_modes"],
        currencies=catalog["currencies"],
        document_types=catalog["document_types"],
        allowed_file_extensions=sorted(ALLOWED_UPLOAD_TYPES),
        max_upload_mb=settings.max_upload_mb,
        auth_mode=settings.auth_mode,
    )
