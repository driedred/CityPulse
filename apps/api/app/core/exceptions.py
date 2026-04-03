from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette import status

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication is required.") -> None:
        super().__init__(
            message,
            code="authentication_failed",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(AppError):
    def __init__(self, message: str = "You do not have permission for this action.") -> None:
        super().__init__(
            message,
            code="forbidden",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(
            message,
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists.") -> None:
        super().__init__(
            message,
            code="conflict",
            status_code=status.HTTP_409_CONFLICT,
        )


def _build_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _build_error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _build_error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed.",
        details=exc.errors(),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Database integrity error: %s", exc)
    return _build_error_response(
        request,
        status_code=status.HTTP_409_CONFLICT,
        code="integrity_error",
        message="The request conflicts with existing data.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
