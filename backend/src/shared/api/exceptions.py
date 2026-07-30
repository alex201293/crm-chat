"""
Global exception handlers for the application.
Maps domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import structlog

logger = structlog.get_logger()


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class EntityNotFoundError(AppException):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str, entity_id: str | None = None) -> None:
        detail = f"{entity} not found"
        if entity_id:
            detail = f"{entity} with id '{entity_id}' not found"
        super().__init__(
            message=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ENTITY_NOT_FOUND",
            details={"entity": entity, "id": entity_id},
        )


class EntityAlreadyExistsError(AppException):
    """Raised when attempting to create a duplicate entity."""

    def __init__(self, entity: str, field: str, value: str) -> None:
        super().__init__(
            message=f"{entity} with {field} '{value}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code="ENTITY_ALREADY_EXISTS",
            details={"entity": entity, "field": field, "value": value},
        )


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_FAILED",
        )


class AuthorizationError(AppException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_FAILED",
        )


class RateLimitExceededError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__(
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after_seconds": retry_after},
        )


class ValidationError_(AppException):
    """Raised when domain validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {},
        )


class TenantNotFoundError(AppException):
    """Raised when tenant context cannot be resolved."""

    def __init__(self) -> None:
        super().__init__(
            message="Tenant not found or not provided",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="TENANT_NOT_FOUND",
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Application exception",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.warning(
            "Validation error",
            path=request.url.path,
            errors=exc.error_count(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                }
            },
        )
