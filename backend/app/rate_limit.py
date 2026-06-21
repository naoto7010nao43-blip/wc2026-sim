"""Minimal in-memory per-IP rate limiter for the few endpoints that mutate
shared state or run CPU-heavy simulation work (tournament reset, ad-hoc
match/round-robin simulation). No third-party dependency on purpose --
this app runs as a single Render free-tier worker, so in-process state is
sufficient, and a small amount of self-contained code is easier to audit
than pulling in an unreviewed rate-limiting package for a handful of
routes.

Not a substitute for the real fix (per-user state) if this app ever grows
multi-instance/multi-worker deployment; at that point this needs to move
to a shared store (e.g. Redis) since each worker would track its own
counts independently.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_WINDOW_SECONDS = 60.0
_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Render/Vercel sit behind a proxy; the real client IP is the first
    # entry in X-Forwarded-For when present, falling back to the direct
    # peer address (e.g. local dev).
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(max_per_minute: int):
    """FastAPI dependency factory: raises 429 once a client exceeds
    `max_per_minute` requests to this route within a rolling 60s window."""

    def dependency(request: Request) -> None:
        key = f"{request.url.path}:{_client_ip(request)}"
        now = time.monotonic()
        bucket = _buckets[key]
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= max_per_minute:
            raise HTTPException(status_code=429, detail="Too many requests -- please slow down and try again shortly.")
        bucket.append(now)

    return dependency


def reset() -> None:
    """Test-only hook to clear all tracked request counts between tests --
    the bucket store is module-level/global, so without this, unrelated
    tests sharing a process (pytest's default) would leak rate-limit state
    into each other."""
    _buckets.clear()
