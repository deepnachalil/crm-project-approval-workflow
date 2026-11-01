from functools import lru_cache

from app.config import get_settings
from app.storage.base import StorageService


@lru_cache
def get_storage() -> StorageService:
    settings = get_settings()
    if settings.storage_backend == "s3":
        from app.storage.s3 import S3Storage

        return S3Storage(settings.s3_bucket_name, settings.aws_region, settings.download_url_expires_seconds)
    from app.storage.local import LocalStorage

    return LocalStorage(settings.local_storage_dir)
