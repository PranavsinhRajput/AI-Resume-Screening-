"""In-memory sliding-window rate limiter keyed by owner_id (architecture.md §8.4)."""

import time
from collections import deque
from threading import Lock

from app.errors import AppError


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, owner_id: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(owner_id, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                raise AppError(429, "rate_limited")
            hits.append(now)
            # Opportunistic cleanup of idle users.
            if len(self._hits) > 5000:
                for key in [k for k, v in self._hits.items() if not v]:
                    del self._hits[key]


_limiter: SlidingWindowLimiter | None = None


def get_search_limiter(limit: int) -> SlidingWindowLimiter:
    global _limiter
    if _limiter is None or _limiter.limit != limit:
        _limiter = SlidingWindowLimiter(limit)
    return _limiter
