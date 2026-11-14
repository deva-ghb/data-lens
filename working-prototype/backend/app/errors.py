"""The API error contract.

Every error response body is JSON `{"code": str, "message": str}`.
`code` is a stable machine-readable value the frontend can branch on.
`message` is plain language a person can read on screen.

Raise `ApiError(status, code, message)` for a specific error.
A plain `HTTPException` is also accepted: its status picks the code, and a string
detail becomes the message.
"""

from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

INVALID_INPUT = "invalid_input"

_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "too_large",
    422: INVALID_INPUT,
    429: "too_many_requests",
    500: "server_error",
    503: "unavailable",
}

_MESSAGES: dict[int, str] = {
    400: "The request could not be processed. Please check it and try again.",
    401: "Please sign in to continue.",
    403: "You do not have access to this.",
    404: "We could not find what you asked for.",
    405: "This action is not available here.",
    409: "This changed while you were working on it. Please refresh and try again.",
    413: "The file or request is too large.",
    422: "Some details are missing or not valid.",
    429: "Too many requests. Please wait a moment and try again.",
    500: "Something went wrong on our side. Please try again.",
    503: "This service is not available right now. Please try again later.",
}

_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}


class ApiError(HTTPException):
    """An HTTP error with an explicit contract code and a plain-language message."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
            headers=headers,
        )


def _code_for(status_code: int) -> str:
    if status_code in _CODES:
        return _CODES[status_code]
    return "server_error" if status_code >= 500 else "error"


def _phrase(status_code: int) -> str | None:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return None


def _message_for(status_code: int) -> str:
    if status_code in _MESSAGES:
        return _MESSAGES[status_code]
    return _phrase(status_code) or "The request could not be completed."


def error_body(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _http_exception_body(exc: StarletteHTTPException) -> dict[str, str]:
    detail = exc.detail
    if isinstance(detail, dict):
        code, message = detail.get("code"), detail.get("message")
        if isinstance(code, str) and isinstance(message, str):
            return error_body(code, message)
    code = _code_for(exc.status_code)
    # Starlette fills an absent detail with the status phrase; prefer our plain wording.
    if isinstance(detail, str) and detail and detail != _phrase(exc.status_code):
        return error_body(code, detail)
    return error_body(code, _message_for(exc.status_code))


def _field_name(location: tuple | list) -> str:
    parts = [str(part) for part in location]
    if parts and parts[0] in _LOCATION_PREFIXES:
        parts = parts[1:]
    return ".".join(parts)


def validation_message(exc: RequestValidationError) -> str:
    fields: list[str] = []
    for error in exc.errors():
        name = _field_name(error.get("loc", ()))
        if name and name not in fields:
            fields.append(name)
    if not fields:
        return "The details sent could not be read. Please check them and try again."
    return "Please check these details: " + ", ".join(fields) + "."


async def _handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_http_exception_body(exc),
        headers=getattr(exc, "headers", None),
    )


async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(INVALID_INPUT, validation_message(exc)),
    )


async def _handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content=error_body("server_error", _MESSAGES[500]))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
