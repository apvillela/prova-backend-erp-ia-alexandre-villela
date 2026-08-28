import logging
from typing import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from erp_api.exceptions.domain import (
    ConflictError,
    ErpApiError,
    ExternalServiceError,
    NotFoundError,
)

log = logging.getLogger(__name__)

_DOMAIN_STATUS_CODES: dict[type[ErpApiError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    ExternalServiceError: 502,
}

_INTERNAL_ERROR_MESSAGE = "Erro interno inesperado."


def _error_response(
    status_code: int, messages: list[str], headers: Mapping[str, str] | None = None
) -> JSONResponse:
    """Formato único de erro da API: `{"detail": [{"msg": ...}]}` (ver `api.ErrorResponse`)."""
    return JSONResponse(
        status_code=status_code,
        content={"detail": [{"msg": message} for message in messages]},
        headers=headers,
    )


async def validation_exception_handler(_: Request, exc: Exception) -> Response:
    if not isinstance(exc, RequestValidationError):
        raise exc

    messages = [
        f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}" for error in exc.errors()
    ]

    return _error_response(422, messages)


async def http_exception_handler(_: Request, exc: Exception) -> Response:
    if not isinstance(exc, StarletteHTTPException):
        raise exc

    detail = exc.detail
    if isinstance(detail, list):
        messages = [
            str(item.get("msg", item)) if isinstance(item, dict) else str(item) for item in detail
        ]
    else:
        messages = [str(detail)]

    return _error_response(exc.status_code, messages, exc.headers)


async def domain_exception_handler(_: Request, exc: Exception) -> Response:
    status_code = 500
    for exception_type, code in _DOMAIN_STATUS_CODES.items():
        if isinstance(exc, exception_type):
            status_code = code
            break

    message = str(exc) or type(exc).__name__
    if status_code >= 500:
        log.exception(f"Erro de domínio sem status mapeado: {message}")
        message = _INTERNAL_ERROR_MESSAGE

    return _error_response(status_code, [message])


async def unhandled_exception_handler(_: Request, exc: Exception) -> Response:
    log.exception(f"Erro não tratado: {exc}")

    return _error_response(500, [_INTERNAL_ERROR_MESSAGE])


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(ErpApiError, domain_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
