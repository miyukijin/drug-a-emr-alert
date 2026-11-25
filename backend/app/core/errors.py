"""Uniform error envelope: {"error": {"code", "message", "request_id", "details"}}."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("emralert")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, details: object | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ModelUnavailableError(AppError):
    status_code = 503
    code = "model_unavailable"


class InvalidInputError(AppError):
    status_code = 422
    code = "invalid_input"


def _envelope(request: Request, status: int, code: str, message: str, details: object | None = None):
    rid = getattr(request.state, "request_id", None)
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message, "request_id": rid, "details": details}})


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _envelope(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(x) for x in e["loc"] if x != "body"), "message": e["msg"]} for e in exc.errors()]
        return _envelope(request, 422, "validation_error", "Request payload failed validation", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return _envelope(request, exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error request_id=%s", getattr(request.state, "request_id", None))
        return _envelope(request, 500, "internal_error", "Unexpected server error; quote the request_id to support")
