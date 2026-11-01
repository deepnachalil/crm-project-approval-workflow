from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import Email, NonEmptyStr, NormalizedUpper, ORMModel

GST_PATTERN = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
GstNumber = Annotated[str, NormalizedUpper, StringConstraints(pattern=GST_PATTERN)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9][0-9\s\-()]{6,19}$")]
Currency = Annotated[str, NormalizedUpper, StringConstraints(pattern=r"^[A-Z]{3}$")]


class PrimaryContact(BaseModel):
    name: NonEmptyStr = Field(max_length=255)
    designation: NonEmptyStr = Field(max_length=255)
    phone: Phone
    email: Email


class ClientIn(BaseModel):
    legal_entity_name: NonEmptyStr = Field(max_length=255)
    registered_address: NonEmptyStr
    billing_address: NonEmptyStr
    mode_of_payment: NonEmptyStr
    gst_number: GstNumber | None = None
    billing_currency: Currency
    primary_contact: PrimaryContact


class ClientOut(ORMModel):
    id: int
    legal_entity_name: str
    registered_address: str
    billing_address: str
    mode_of_payment: str
    gst_number: str | None
    billing_currency: str
    primary_contact: PrimaryContact
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, c) -> "ClientOut":
        return cls(
            id=c.id,
            legal_entity_name=c.legal_entity_name,
            registered_address=c.registered_address,
            billing_address=c.billing_address,
            mode_of_payment=c.mode_of_payment,
            gst_number=c.gst_number,
            billing_currency=c.billing_currency,
            primary_contact=PrimaryContact(
                name=c.contact_name,
                designation=c.contact_designation,
                phone=c.contact_phone,
                email=c.contact_email,
            ),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )


class ClientRef(ORMModel):
    id: int
    legal_entity_name: str
