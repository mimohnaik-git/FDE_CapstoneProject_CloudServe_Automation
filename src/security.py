"""Authentication and bounded single-process rate limiting for operational APIs."""

from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import os
import secrets
import threading
import time
from typing import Annotated, Deque, Dict

from fastapi import Header, HTTPException, status


DEFAULT_RATE_LIMIT_PER_MINUTE = 60
MAX_RATE_LIMIT_PER_MINUTE = 10_000


class InMemoryRateLimiter:
    """Thread-safe fixed-window request limiter for one application process."""

    def __init__(self) -> None:
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(
        self,
        identity: str,
        *,
        limit: int,
        now: float | None = None,
    ) -> bool:
        current = time.monotonic() if now is None else float(now)
        cutoff = current - 60.0

        with self._lock:
            requests = self._requests[identity]

            while requests and requests[0] <= cutoff:
                requests.popleft()

            if len(requests) >= limit:
                return False

            requests.append(current)
            return True

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


api_rate_limiter = InMemoryRateLimiter()


def _configured_api_key() -> str:
    key = os.getenv("SUPPORT_API_KEY", "").strip()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    return key


def _configured_rate_limit() -> int:
    raw = os.getenv(
        "SUPPORT_API_RATE_LIMIT_PER_MINUTE",
        str(DEFAULT_RATE_LIMIT_PER_MINUTE),
    ).strip()

    try:
        limit = int(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API rate limiting is not configured correctly.",
        ) from exc

    if limit < 1 or limit > MAX_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API rate limiting is not configured correctly.",
        )

    return limit


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, separator, credential = authorization.partition(" ")

    if (
        not separator
        or scheme.lower() != "bearer"
        or not credential.strip()
    ):
        return None

    return credential.strip()


def _configured_reviewer_api_key() -> str:
    key = os.getenv("SUPPORT_REVIEWER_API_KEY", "").strip()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reviewer API authentication is not configured.",
        )

    processing_key = os.getenv("SUPPORT_API_KEY", "").strip()

    if processing_key and secrets.compare_digest(key, processing_key):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reviewer API credential must be distinct from processing API credential.",
        )

    return key


def require_api_access(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Authenticate an operational API request and apply local rate limiting."""

    configured_key = _configured_api_key()
    supplied_key = _bearer_token(authorization)

    if (
        supplied_key is None
        or not secrets.compare_digest(supplied_key, configured_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API credential.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    identity = hashlib.sha256(supplied_key.encode("utf-8")).hexdigest()

    if not api_rate_limiter.allow(
        identity,
        limit=_configured_rate_limit(),
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded.",
        )

def require_reviewer_access(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Authenticate access to internal human-review surfaces."""

    configured_key = _configured_reviewer_api_key()
    supplied_key = _bearer_token(authorization)

    if (
        supplied_key is None
        or not secrets.compare_digest(supplied_key, configured_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing reviewer credential.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    identity = hashlib.sha256(
        f"reviewer:{supplied_key}".encode("utf-8")
    ).hexdigest()

    if not api_rate_limiter.allow(
        identity,
        limit=_configured_rate_limit(),
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Reviewer API rate limit exceeded.",
        )
