"""Environment-based configuration.

All settings come from environment variables (or a local `.env` file during
development). Nothing secret has a default value here.
"""
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "aws"] = "local"

    # --- Database -------------------------------------------------------------
    # Local: set DATABASE_URL directly.
    # AWS:   leave DATABASE_URL empty and provide DB_HOST/DB_PORT/DB_NAME plus
    #        DB_SECRET_ARN (RDS-managed Secrets Manager secret with username/password).
    database_url: str | None = None
    db_host: str | None = None
    db_port: int = 5432
    db_name: str | None = None
    db_secret_arn: str | None = None

    # --- Authentication ---------------------------------------------------------
    # local:   username/password against the users table, HS256 JWT issued by this API.
    # cognito: API Gateway Cognito authorizer validates the token; the API maps the
    #          token's email claim to a user row (role comes from the database).
    auth_mode: Literal["local", "cognito"] = "local"
    jwt_secret: str | None = None
    jwt_expires_minutes: int = 480
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None

    # --- File storage -----------------------------------------------------------
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "./storage"
    # Public base URL of this API, used to build local download links.
    public_api_url: str = "http://localhost:8000"
    s3_bucket_name: str | None = None
    aws_region: str | None = None
    download_url_expires_seconds: int = 300
    max_upload_mb: int = 5

    # --- HTTP -------------------------------------------------------------------
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @model_validator(mode="after")
    def _check_consistency(self) -> "Settings":
        if not self.database_url and not (self.db_host and self.db_name and self.db_secret_arn):
            raise ValueError("Set DATABASE_URL, or DB_HOST + DB_NAME + DB_SECRET_ARN")
        if (self.auth_mode == "local" or self.storage_backend == "local") and not self.jwt_secret:
            raise ValueError("JWT_SECRET is required when AUTH_MODE=local or STORAGE_BACKEND=local")
        if self.storage_backend == "s3" and not self.s3_bucket_name:
            raise ValueError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Allowed upload types: extension -> accepted MIME types.
ALLOWED_UPLOAD_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}
