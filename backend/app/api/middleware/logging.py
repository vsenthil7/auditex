"""Auditex -- Structured JSON request logging middleware (Phase 11 Item 5).

Emits one JSON log line per request, with:
  - request_id (uuid4) -- also set in X-Request-ID response header
  - method, path, query_string
  - status_code, duration_ms
  - identity (from X-API-Key if present, else client ip)
  - user_agent

Log records go through python logging -- configure the root handler in
app.main to send them wherever you want (stdout, elastic, etc).
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("auditex.access")


def _identity(request: Request) -> str:
    """Prefer API key; fall back to client host; finally "unknown"."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"k:{api_key}"
    if request.client is not None:
        return f"ip:{request.client.host}"
    return "ip:unknown"


def _build_log_record(
    request_id: str,
    method: str,
    path: str,
    query_string: str,
    status_code: int,
    duration_ms: int,
    identity: str,
    user_agent: str,
) -> str:
    """Serialise the access-log fields to a single JSON line."""
    return json.dumps(
        {
            "request_id": request_id,
            "method": method,
            "path": path,
            "query": query_string or "",
            "status": status_code,
            "duration_ms": duration_ms,
            "identity": identity,
            "user_agent": user_agent,
        },
        separators=(",", ":"),
        sort_keys=True,
    )


class JSONLoggingMiddleware(BaseHTTPMiddleware):
    """Logs one JSON line per HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.monotonic()
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception:
            duration_ms = int((time.monotonic() - start) * 1000)
            line = _build_log_record(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                query_string=request.url.query,
                status_code=500,
                duration_ms=duration_ms,
                identity=_identity(request),
                user_agent=request.headers.get("user-agent", ""),
            )
            logger.error(line)
            raise
        duration_ms = int((time.monotonic() - start) * 1000)
        line = _build_log_record(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_string=request.url.query,
            status_code=status_code,
            duration_ms=duration_ms,
            identity=_identity(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        if status_code >= 500:
            logger.error(line)
        elif status_code >= 400:
            logger.warning(line)
        else:
            logger.info(line)
        response.headers["X-Request-ID"] = request_id
        return response
