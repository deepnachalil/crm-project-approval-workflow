from typing import Literal, Protocol

Disposition = Literal["inline", "attachment"]


class StorageService(Protocol):
    """File storage for contract documents. Implementations: local disk, Amazon S3."""

    def save(self, key: str, data: bytes, content_type: str) -> None: ...

    def delete(self, key: str) -> None: ...

    def download_url(self, key: str, file_name: str, content_type: str, disposition: Disposition) -> str:
        """Short-lived URL from which the browser can view/download the file."""
        ...
