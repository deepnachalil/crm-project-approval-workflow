import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, ValidationInfo, field_validator, model_validator

from app.schemas.common import Email, NonEmptyStr, NormalizedUpper, ORMModel

INDIA = "IN"
# Indian GSTIN: 2-digit state code + PAN (5 letters, 4 digits, 1 letter) + entity code + 'Z' + check character.
GST_PATTERN = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
# Non-Indian entities have no GSTIN; they enter their local tax registration number (VAT, EIN, TRN, ...).
TAX_ID_PATTERN = r"^[A-Z0-9][A-Z0-9 ./-]{3,18}[A-Z0-9]$"
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9][0-9\s\-()]{6,19}$")]
Currency = Annotated[str, NormalizedUpper, StringConstraints(pattern=r"^[A-Z]{3}$")]
CountryCode = Annotated[str, NormalizedUpper, StringConstraints(pattern=r"^[A-Z]{2}$")]


class PrimaryContact(BaseModel):
    name: NonEmptyStr = Field(max_length=255)
    designation: NonEmptyStr = Field(max_length=255)
    phone: Phone
    email: Email


class ClientIn(BaseModel):
    legal_entity_name: NonEmptyStr = Field(max_length=255)
    registered_address: NonEmptyStr
    # Optional: when omitted or blank, the billing address is the same as the registered address.
    billing_address: str | None = None
    mode_of_payment: NonEmptyStr
    country: CountryCode
    # Mandatory for every client. India: a valid GSTIN; other countries: their tax registration number.
    gst_number: str | None = Field(default=None, validate_default=True)
    billing_currency: Currency
    primary_contact: PrimaryContact

    @field_validator("billing_address", "gst_number", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return (v.strip() or None) if isinstance(v, str) else v

    @field_validator("gst_number")
    @classmethod
    def _check_gst(cls, v: str | None, info: ValidationInfo) -> str:
        if not v:
            raise ValueError("GST Number is required")
        v = v.upper()
        if info.data.get("country") == INDIA:
            if not re.fullmatch(GST_PATTERN, v):
                raise ValueError("Enter a valid 15-character GSTIN (e.g. 29ABCDE1234F1Z5)")
        elif not re.fullmatch(TAX_ID_PATTERN, v):
            raise ValueError("Enter a valid tax registration number (5-20 letters or digits)")
        return v

    @model_validator(mode="after")
    def _default_billing_to_registered(self) -> "ClientIn":
        if self.billing_address is None:
            self.billing_address = self.registered_address
        return self


class ClientOut(ORMModel):
    id: int
    legal_entity_name: str
    registered_address: str
    billing_address: str
    mode_of_payment: str
    country: str
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
            country=c.country,
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
