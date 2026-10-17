"""Resolve one browser credential from raw ASGI headers before any normalization."""

import re

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

SESSION_AUTH_MARKER = "session-cookie"
SESSION_AUTHORIZATION = "Bearer " + SESSION_AUTH_MARKER
_TOKEN = re.compile(r"[A-Za-z0-9._~+/-]+=*\Z", re.ASCII)


def _reject(detail="Invalid or conflicting authentication credentials"):
    raise HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def resolve_credentials(headers: list[tuple[bytes, bytes]]) -> str | None:
    """No last-header/cookie wins, invalid-header fallback, or mixed identities."""
    auth = [value for name, value in headers if name.lower() == b"authorization"]
    if len(auth) > 1:
        _reject()
    token = None
    if auth:
        try:
            value = auth[0].decode("ascii").strip(" \t")
        except UnicodeError:
            _reject()
        scheme, separator, token = value.partition(" ")
        if not separator or scheme.lower() != "bearer" or not _valid_token(token):
            _reject()
    cookies = []
    for name, raw in headers:
        if name.lower() != b"cookie":
            continue
        if len(raw) > 65536:
            _reject()
        for part in raw.split(b";"):
            key, separator, value = part.strip().partition(b"=")
            if key.strip() != b"access_token":
                continue
            if not separator or key != b"access_token":
                _reject()
            try:
                cookie = value.decode("ascii")
            except UnicodeError:
                _reject()
            if not _valid_token(cookie) or cookie.lower() == SESSION_AUTH_MARKER:
                _reject()
            cookies.append(cookie)
    if len(cookies) > 1:
        _reject()
    cookie = cookies[0] if cookies else None
    if token and token.lower() == SESSION_AUTH_MARKER:
        if not cookie:
            _reject("Missing Authorization token")
        return cookie
    if token and cookie and token != cookie:
        _reject()
    return token or cookie


def _valid_token(value):
    return isinstance(value, str) and 0 < len(value) <= 32768 and _TOKEN.fullmatch(value) is not None


def request_token(request: Request) -> str:
    token = resolve_credentials(request.scope.get("headers", []))
    if not token:
        _reject("Missing Authorization token")
    return token


class AuthCookieMiddleware:
    """Preserve bearer, cookie and frontend-marker wire forms without ambiguity.

    Resolving credentials is not verification. Downstream identity dependencies
    must still authenticate the selected token. Raw headers are checked before
    replacement so duplicate credentials cannot be collapsed into a trusted one.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        try:
            token = resolve_credentials(scope.get("headers", []))
        except HTTPException as exc:
            return await JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
                                      headers=exc.headers)(scope, receive, send)
        if token:
            scope = {**scope, "headers": [
                (key, value) for key, value in scope.get("headers", []) if key.lower() != b"authorization"
            ] + [(b"authorization", ("Bearer " + token).encode("ascii"))]}
        await self.app(scope, receive, send)
