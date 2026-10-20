import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

DEFAULT_MESSAGES: dict[str, str] = {
    "unauthorized": "Your session expired. Please log in again.",
    "forbidden": "You don't have permission to do that.",
    "pending_approval": "Your account is waiting for admin approval.",
    "account_rejected": "Your account request was not approved. Contact the administrator.",
    "read_only": "Admins viewing another user's library can't make changes.",
    "not_found": "We couldn't find that.",
    "validation_error": "Some fields are invalid.",
    "no_resumes_ready": "Upload and process resumes first.",
    "rate_limited": "Too many searches. Try again in a minute.",
    "internal_error": "Something went wrong. Please try again.",
}


class AppError(Exception):
    """An error that maps directly to the API error format {"error": {"code", "message"}}."""

    def __init__(self, status_code: int, code: str, message: str | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, DEFAULT_MESSAGES["internal_error"])
        super().__init__(self.message)


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _format_validation_error(exc: RequestValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
        field = ".".join(loc) or "request"
        parts.append(f"{field}: {err.get('msg', 'invalid value')}")
    return "; ".join(parts) or DEFAULT_MESSAGES["validation_error"]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422, content=error_body("validation_error", _format_validation_error(exc))
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            422: "validation_error",
            429: "rate_limited",
        }
        code = codes.get(exc.status_code, "internal_error" if exc.status_code >= 500 else "validation_error")
        message = DEFAULT_MESSAGES.get(code, str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=error_body(code, message))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error: %s", type(exc).__name__, exc_info=exc)
        return JSONResponse(
            status_code=500, content=error_body("internal_error", DEFAULT_MESSAGES["internal_error"])
        )
