"""Shared request tracing and log-correlation helpers."""

from __future__ import annotations

from contextvars import ContextVar
import logging
from typing import Mapping
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_service_name_var: ContextVar[str | None] = ContextVar("service_name", default=None)

DEFAULT_LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s "
    "service=%(service_name)s request_id=%(request_id)s correlation_id=%(correlation_id)s %(message)s"
)


def _generate_trace_id() -> str:
    return str(uuid4())


def _header_lookup(headers: Mapping[str, str], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if str(key).lower() == target:
            return str(value)
    return None


def _set_header(headers: dict[str, str], name: str, value: str) -> None:
    target = name.lower()
    for key in list(headers.keys()):
        if key.lower() == target and key != name:
            headers.pop(key, None)
    headers[name] = value


def get_request_id(default: str | None = "-") -> str | None:
    return _request_id_var.get() or default


def get_correlation_id(default: str | None = "-") -> str | None:
    return _correlation_id_var.get() or default


def get_service_name(default: str | None = "-") -> str | None:
    return _service_name_var.get() or default


def build_trace_headers(
    headers: Mapping[str, str] | None = None,
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, str]:
    """Return a header dict that always carries canonical trace identifiers."""
    merged = {str(key): str(value) for key, value in (headers or {}).items()}
    resolved_request_id = (
        request_id
        or _header_lookup(merged, REQUEST_ID_HEADER)
        or get_request_id(default=None)
        or _generate_trace_id()
    )
    resolved_correlation_id = (
        correlation_id
        or _header_lookup(merged, CORRELATION_ID_HEADER)
        or get_correlation_id(default=None)
        or resolved_request_id
    )
    _set_header(merged, REQUEST_ID_HEADER, resolved_request_id)
    _set_header(merged, CORRELATION_ID_HEADER, resolved_correlation_id)
    return merged


class RequestTracingLogFilter(logging.Filter):
    """Inject request tracing context into log records."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id("-")
        record.correlation_id = get_correlation_id("-")
        record.service_name = _service_name_var.get() or self.service_name
        return True


def configure_logging(
    service_name: str,
    *,
    level: int | str = logging.INFO,
    log_format: str = DEFAULT_LOG_FORMAT,
) -> logging.Logger:
    """Attach request-aware logging filters and formatters to root handlers."""
    root_logger = logging.getLogger()
    if isinstance(level, str):
        level = getattr(logging, str(level).upper(), logging.INFO)
    root_logger.setLevel(level)

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        root_logger.addHandler(handler)

    formatter = logging.Formatter(log_format)
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
        for item in list(handler.filters):
            if isinstance(item, RequestTracingLogFilter):
                handler.removeFilter(item)
        handler.addFilter(RequestTracingLogFilter(service_name))

    return logging.getLogger(service_name)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Generate or preserve request identifiers and expose them on responses."""

    def __init__(self, app, *, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or _generate_trace_id()
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.service_name = self.service_name

        request_token = _request_id_var.set(request_id)
        correlation_token = _correlation_id_var.set(correlation_id)
        service_token = _service_name_var.set(self.service_name)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            _service_name_var.reset(service_token)
            _correlation_id_var.reset(correlation_token)
            _request_id_var.reset(request_token)
