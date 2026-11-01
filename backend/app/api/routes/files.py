"""Serves files for the *local* storage backend only (the S3 backend uses presigned URLs).
Access is granted by the short-lived signed token issued via /contracts/{id}/download-url."""
from urllib.parse import quote

from fastapi import APIRouter, Response

from app.errors import NotFoundError
from app.storage import get_storage
from app.storage.local import LocalStorage

router = APIRouter(tags=["files"], include_in_schema=False)


@router.get("/files/{token}")
def serve_file(token: str) -> Response:
    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise NotFoundError("Not found")
    claims = LocalStorage.parse_download_token(token)
    data = storage.read(claims["sub"])
    disposition = "inline" if claims.get("disp") == "inline" else "attachment"
    return Response(
        content=data,
        media_type=claims.get("ct", "application/octet-stream"),
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(claims.get('fn', 'document'))}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
