"""Domain errors. Services raise these; the API layer maps them to a consistent
JSON error envelope: {"error": {"code": ..., "message": ..., "details": [...]}}.
"""
from typing import Any


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class AuthenticationError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationFailedError(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"


def issue(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}
