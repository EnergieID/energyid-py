import asyncio
from collections import deque
from time import monotonic
from typing import Deque


class AsyncRequestLimiter:
    """Simple in-process limiter for request rate and concurrency."""

    def __init__(
        self,
        *,
        max_concurrency: int | None,
        max_requests_per_window: int | None,
        rate_limit_window_seconds: float,
    ):
        if max_concurrency is not None and max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1 or None")
        if max_requests_per_window is not None and max_requests_per_window < 1:
            raise ValueError("max_requests_per_window must be >= 1 or None")
        if rate_limit_window_seconds <= 0:
            raise ValueError("rate_limit_window_seconds must be > 0")

        self._semaphore = (
            asyncio.Semaphore(max_concurrency) if max_concurrency is not None else None
        )
        self._max_requests_per_window = max_requests_per_window
        self._window = rate_limit_window_seconds
        self._timestamps: Deque[float] = deque()
        self._timestamps_lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self._semaphore is not None:
            await self._semaphore.acquire()
        try:
            await self._acquire_rate_slot()
        except Exception:
            if self._semaphore is not None:
                self._semaphore.release()
            raise

    def release(self) -> None:
        if self._semaphore is not None:
            self._semaphore.release()

    async def _acquire_rate_slot(self) -> None:
        if self._max_requests_per_window is None:
            return

        while True:
            wait_for = 0.0
            async with self._timestamps_lock:
                now = monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._max_requests_per_window:
                    self._timestamps.append(now)
                    return

                wait_for = self._window - (now - self._timestamps[0])

            await asyncio.sleep(max(wait_for, 0.0))
