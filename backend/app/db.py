"""Database engine / session management (local PostgreSQL or RDS)."""
import json
from collections.abc import Iterator
from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def _url_from_secret(settings: Settings) -> str:
    """Build the connection URL from an RDS-managed Secrets Manager secret.

    The Lambda execution role grants secretsmanager:GetSecretValue on this one
    secret; no credentials are stored in code or environment variables.
    """
    import boto3  # provided by the Lambda runtime

    client = boto3.client("secretsmanager", region_name=settings.aws_region)
    secret = json.loads(client.get_secret_value(SecretId=settings.db_secret_arn)["SecretString"])
    user = quote_plus(secret["username"])
    password = quote_plus(secret["password"])
    return (
        f"postgresql+psycopg://{user}:{password}@{settings.db_host}:{settings.db_port}"
        f"/{settings.db_name}?sslmode=require"
    )


def resolve_database_url(settings: Settings) -> str:
    return settings.database_url or _url_from_secret(settings)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    url = resolve_database_url(settings)
    kwargs: dict = {"pool_pre_ping": True}
    if settings.app_env == "aws":
        # One Lambda container handles one request at a time.
        kwargs.update(pool_size=1, max_overflow=0)
    return create_engine(url, **kwargs)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    # expire_on_commit (default) makes responses built after a commit reload fresh state.
    return sessionmaker(bind=get_engine(), autoflush=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
