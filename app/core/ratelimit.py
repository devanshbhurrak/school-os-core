"""In-process sliding-window rate limiter (Phase 1).

Per-IP, per-route limits for login and password reset. In-memory only: each
process enforces its own window, which is fine for a single worker in Phase 1.
Milestone 7 replaces this with a Redis-backed limiter (production, multi-worker).
"""
from __future__ import annotations

import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, limit: int, window_seconds: float) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds). Not thread-safe by design —
        FastAPI runs handlers on one event loop per worker."""
        now = time.monotonic()
        queue = self._hits.setdefault(key, deque())
        while queue and queue[0] <= now - window_seconds:
            queue.popleft()

        if len(queue) >= limit:
            retry_after = max(1, int(window_seconds - (now - queue[0])) + 1)
            return False, retry_after

        queue.append(now)
        return True, 0


login_limiter = SlidingWindowLimiter()
password_reset_limiter = SlidingWindowLimiter()


def login_rate_limit_key(ip: str | None) -> str:
    return f"login:{ip or 'unknown'}"


def password_reset_rate_limit_key(ip: str | None) -> str:
    return f"password-reset:{ip or 'unknown'}"
