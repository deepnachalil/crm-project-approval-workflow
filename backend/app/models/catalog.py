"""Reference catalog: rate cards and standard job categories (seeded from catalog.json)."""
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RateCard(Base):
    __tablename__ = "rate_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class JobCategory(Base):
    __tablename__ = "job_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    default_rate_card_id: Mapped[int | None] = mapped_column(ForeignKey("rate_cards.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    default_rate_card: Mapped[RateCard | None] = relationship(lazy="joined")
