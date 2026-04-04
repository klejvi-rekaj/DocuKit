import logging
import threading
import time
from collections import deque

from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.time()
        threshold = now - window_seconds

        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] < threshold:
                events.popleft()

            if len(events) >= limit:
                logger.warning("Rate limit exceeded for key=%s window=%s limit=%s", key, window_seconds, limit)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait a moment and try again.",
                )

            events.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = InMemoryRateLimiter()
