from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Client(TimestampMixin, Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    legal_entity_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    registered_address: Mapped[str] = mapped_column(Text, nullable=False)
    billing_address: Mapped[str] = mapped_column(Text, nullable=False)
    mode_of_payment: Mapped[str] = mapped_column(String(64), nullable=False)
    # ISO 3166-1 alpha-2 country of registration. GST is mandatory when this is "IN".
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    gst_number: Mapped[str | None] = mapped_column(String(15))
    billing_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_designation: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
