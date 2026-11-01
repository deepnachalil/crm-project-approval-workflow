"""Local-disk storage for development. Download links point back at this API's
/files/{token} endpoint with a short-lived signed token (mimicking S3 presigned URLs)."""
from datetime import timedelta
from pathlib import Path

from app.config import get_settings
from app.errors import NotFoundError
from app.security.tokens import DOWNLOAD_AUDIENCE, decode_token, encode_token
from app.storage.base import Disposition


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Invalid storage key")
        return path

    def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def read(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise NotFoundError("File not found")
        return path.read_bytes()

    def download_url(self, key: str, file_name: str, content_type: str, disposition: Disposition) -> str:
        settings = get_settings()
        token = encode_token(
            key,
            DOWNLOAD_AUDIENCE,
            timedelta(seconds=settings.download_url_expires_seconds),
            {"fn": file_name, "ct": content_type, "disp": disposition},
        )
        return f"{settings.public_api_url.rstrip('/')}/files/{token}"

    @staticmethod
    def parse_download_token(token: str) -> dict:
        return decode_token(token, DOWNLOAD_AUDIENCE)
