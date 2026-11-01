from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JobCategory, RateCard


def list_rate_cards(db: Session) -> list[RateCard]:
    return list(db.scalars(select(RateCard).where(RateCard.is_active.is_(True)).order_by(RateCard.name)))


def get_rate_card(db: Session, rate_card_id: int) -> RateCard | None:
    return db.get(RateCard, rate_card_id)


def list_job_categories(db: Session) -> list[JobCategory]:
    return list(db.scalars(select(JobCategory).where(JobCategory.is_active.is_(True)).order_by(JobCategory.name)))


def get_job_category(db: Session, job_category_id: int) -> JobCategory | None:
    return db.get(JobCategory, job_category_id)
