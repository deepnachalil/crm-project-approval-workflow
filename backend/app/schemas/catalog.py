from pydantic import BaseModel

from app.schemas.common import ORMModel


class RateCardOut(ORMModel):
    id: int
    code: str
    name: str
    description: str | None
    currency: str


class JobCategoryOut(ORMModel):
    id: int
    name: str
    default_rate_card: RateCardOut | None


class MetaOut(BaseModel):
    business_units: list[str]
    payment_modes: list[str]
    currencies: list[str]
    document_types: list[str]
    allowed_file_extensions: list[str]
    max_upload_mb: int
    auth_mode: str
