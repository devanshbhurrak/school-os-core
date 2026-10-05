"""Rate limiting — Phase 10: slowapi (decorator-based) + legacy sliding window.

The `limiter` instance (slowapi) is attached to `app.state` in `main.py` and
provides `@limiter.limit(...)` decorators for route-level enforcement.

The `SlidingWindowLimiter` helpers remain for the auth router's manual checks
(login lockout, password-reset) which need fine-grained control over the
error response and per-key logic.
"""
from __future__ import annotations

import time
from collections import deque

from slowapi import Limiter
from slowapi.util import get_remote_address

# ---------------------------------------------------------------------------
# slowapi limiter — attach to app.state in main.py
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Legacy in-process sliding-window limiter (auth routes)
# ---------------------------------------------------------------------------


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
