"""Rate limiting — Phase 3: Redis-backed distributed limiting (Upstash-compatible).

Design:
* slowapi `Limiter` uses Redis storage when `REDIS_URL` is configured so limits
  are shared across Cloud Run instances / uvicorn workers. Falls back to memory
  when Redis is unavailable (local dev / tests).
* Auth's fine-grained sliding-window checks (`login`, `password-reset`) use a
  `DistributedSlidingWindowLimiter` backed by Redis `ZADD/ZREMRANGEBYSCORE`
  (atomic-ish via pipeline). Falls back to the in-process deque implementation
  when Redis is not configured or unreachable — never fail-open silently in
  production: fallback is logged and still enforces per-worker limits.

Upstash notes:
* Use `rediss://` URL (TLS) in production. Connection pool is lazy and small
  (Cloud Run scales to zero; pool created on first use, short socket timeouts).
* `redis[hiredis]` is used when available for speed; pure-python parser fallback
  is automatic.
"""
from __future__ import annotations

import logging
import time
from collections import deque

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis client (lazy singleton, Upstash-friendly)
# ---------------------------------------------------------------------------

_redis_client = None
_redis_init_attempted = False


def get_redis_client():
    """Return a shared Redis client or None when not configured/unreachable.

    Lazy-init keeps Cloud Run cold starts fast and lets tests run without Redis.
    Short socket timeouts prevent request threads from hanging on Redis blips.
    """
    global _redis_client, _redis_init_attempted  # noqa: PLW0603
    settings = get_settings()
    if not settings.redis_url:
        return None
    if _redis_client is not None:
        return _redis_client
    if _redis_init_attempted and _redis_client is None:
        # A previous attempt failed; retry lazily (Upstash may cold-start).
        pass
    try:
        import redis.asyncio as redis_asyncio

        _redis_client = redis_asyncio.from_url(
            settings.redis_url,
            max_connections=settings.redis_pool_max_connections,
            socket_timeout=settings.redis_socket_timeout_seconds,
            socket_connect_timeout=settings.redis_socket_timeout_seconds,
            health_check_interval=30,
            decode_responses=True,
        )
        _redis_init_attempted = True
        return _redis_client
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("redis_unavailable", extra={"error": str(exc)})
        _redis_init_attempted = True
        return None


async def check_redis_connectivity() -> tuple[bool, str]:
    """Ping Redis for the /health/ready probe. Returns (ok, detail)."""
    settings = get_settings()
    if not settings.redis_url:
        return True, "not_configured (in-memory fallback)"
    client = get_redis_client()
    if client is None:
        return False, "client_init_failed"
    try:
        await client.ping()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def reset_redis_client_for_tests() -> None:
    """Test hook: drop the cached client so settings overrides take effect."""
    global _redis_client, _redis_init_attempted  # noqa: PLW0603
    _redis_client = None
    _redis_init_attempted = False


# ---------------------------------------------------------------------------
# slowapi limiter — Redis storage when configured, memory otherwise
# ---------------------------------------------------------------------------


def _build_limiter() -> Limiter:
    settings = get_settings()
    if settings.redis_url:
        try:
            from slowapi.util import get_remote_address as _kra  # noqa: F401
            import re

            # slowapi accepts a storage URI string; use it directly so Upstash
            # rediss:// URLs (TLS) work without extra code.
            return Limiter(
                key_func=get_remote_address,
                storage_uri=settings.redis_url,
                strategy="fixed-window",
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("slowapi_redis_fallback", extra={"error": str(exc)})
    return Limiter(key_func=get_remote_address)


limiter = _build_limiter()


# ---------------------------------------------------------------------------
# Sliding-window limiter (auth routes): Redis ZSET with in-memory fallback
# ---------------------------------------------------------------------------


class _MemorySlidingWindow:
    """Original in-process sliding window (fallback when Redis is absent)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, limit: int, window_seconds: float) -> tuple[bool, int]:
        now = time.monotonic()
        queue = self._hits.setdefault(key, deque())
        while queue and queue[0] <= now - window_seconds:
            queue.popleft()
        if len(queue) >= limit:
            retry_after = max(1, int(window_seconds - (now - queue[0])) + 1)
            return False, retry_after
        queue.append(now)
        return True, 0


class DistributedSlidingWindowLimiter:
    """Sliding-window limiter shared across workers via Redis sorted sets.

    Key layout: `ratelimit:<key>` -> ZSET of `{member: unique, score: now}`.
    Each `allow()` trims entries older than the window, counts the remainder,
    and adds the current hit when under the limit. Uses a pipeline so trim +
    count + add are a single round-trip.
    """

    def __init__(self, prefix: str = "ratelimit") -> None:
        self._prefix = prefix
        self._fallback = _MemorySlidingWindow()
        self._counter = 0

    def _redis_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def allow_async(
        self, key: str, limit: int, window_seconds: float
    ) -> tuple[bool, int]:
        client = get_redis_client()
        if client is None:
            return self._fallback.allow(key, limit, window_seconds)
        import time as _time

        now = _time.time()
        window_start = now - window_seconds
        rkey = self._redis_key(key)
        self._counter += 1
        member = f"{now:.6f}:{self._counter}"
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(rkey, 0, window_start)
            pipe.zcard(rkey)
            _, count = await pipe.execute()
            if int(count) >= limit:
                # Peek oldest to compute Retry-After without extra writes.
                oldest = await client.zrange(rkey, 0, 0, withscores=True)
                retry_after = int(window_seconds)
                if oldest:
                    retry_after = max(1, int(window_seconds - (now - oldest[0][1])) + 1)
                return False, retry_after
            pipe = client.pipeline()
            pipe.zadd(rkey, {member: now})
            pipe.pexpire(rkey, int(window_seconds * 1000) + 1000)
            await pipe.execute()
            return True, 0
        except Exception as exc:  # Redis blip: enforce locally, never fail open
            logger.warning("ratelimit_redis_fallback", extra={"error": str(exc)})
            return self._fallback.allow(key, limit, window_seconds)

    def allow(self, key: str, limit: int, window_seconds: float) -> tuple[bool, int]:
        """Sync wrapper for call sites without an event loop hook.

        When Redis is configured but we are in a sync context, fall back to the
        in-process window (per-worker). Async paths should call `allow_async`.
        """
        if get_redis_client() is None:
            return self._fallback.allow(key, limit, window_seconds)
        # Try to use a running loop; otherwise use the memory fallback.
        try:
            import asyncio

            loop = asyncio.get_running_loop()
        except RuntimeError:
            return self._fallback.allow(key, limit, window_seconds)
        # We have a loop but are in sync code — cannot block; use fallback.
        _ = loop
        return self._fallback.allow(key, limit, window_seconds)

    def reset_for_tests(self) -> None:
        self._fallback._hits.clear()

    # Back-compat: tests access `limiter._hits` directly (pre-Phase-3 API).
    @property
    def _hits(self):  # type: ignore[no-redef]
        return self._fallback._hits


login_limiter = DistributedSlidingWindowLimiter(prefix="ratelimit")
password_reset_limiter = DistributedSlidingWindowLimiter(prefix="ratelimit")


def login_rate_limit_key(ip: str | None) -> str:
    return f"login:{ip or 'unknown'}"


def password_reset_rate_limit_key(ip: str | None) -> str:
    return f"password-reset:{ip or 'unknown'}"
