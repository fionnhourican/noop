"""Exponential backoff, full jitter, and HTTP Retry-After header parsing."""

import email.utils
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def parse_retry_after(header_val: Optional[str]) -> Optional[float]:
    """Parse HTTP 429 / 503 Retry-After header.

    Supports:
    1. Integer delta-seconds (e.g. "120")
    2. HTTP-date RFC 7231 (e.g. "Wed, 21 Oct 2026 07:28:00 GMT")

    Returns delay in seconds (>= 0.0), or None if header is missing or unparseable.
    """
    if not header_val:
        return None

    clean = header_val.strip()
    # 1. Delta-seconds
    try:
        val = float(clean)
        return max(0.0, val)
    except ValueError:
        pass

    # 2. HTTP-date
    try:
        dt = email.utils.parsedate_to_datetime(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (dt - now).total_seconds()
        return max(0.0, delta)
    except Exception as e:
        logger.debug("Failed to parse Retry-After header '%s': %s", clean, e)
        return None


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    factor: float = 2.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff with full jitter.

    Full jitter ensures that retries across multiple workers or reconnect loops
    do not synchronize into thundering herds.
    """
    ceiling = min(max_delay, base_delay * (factor ** attempt))
    if not jitter:
        return ceiling
    return random.uniform(0.0, ceiling)


class BackoffManager:
    """Stateful retry and backoff coordinator."""

    def __init__(
        self,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        factor: float = 2.0,
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.factor = factor
        self.attempt = 0
        self.consecutive_failures = 0
        self._next_retry_time: float = 0.0

    def compute_delay(self, retry_after: Optional[float] = None) -> float:
        """Compute the wait duration in seconds before the next retry."""
        if retry_after is not None and retry_after > 0:
            delay = min(self.max_delay, max(self.base_delay, retry_after))
        else:
            delay = calculate_backoff(
                attempt=self.attempt,
                base_delay=self.base_delay,
                max_delay=self.max_delay,
                factor=self.factor,
                jitter=True,
            )
        return delay

    def record_failure(self, retry_after: Optional[float] = None) -> float:
        """Record a failed attempt, increment counters, and return the delay."""
        self.consecutive_failures += 1
        delay = self.compute_delay(retry_after)
        self.attempt += 1
        self._next_retry_time = time.time() + delay
        return delay

    def record_success(self) -> None:
        """Reset backoff counters upon confirmed delivery."""
        self.attempt = 0
        self.consecutive_failures = 0
        self._next_retry_time = 0.0

    @property
    def can_retry_now(self) -> bool:
        """Whether the backoff duration has elapsed."""
        return time.time() >= self._next_retry_time

    @property
    def remaining_wait(self) -> float:
        """Seconds remaining until the next retry is permitted."""
        return max(0.0, self._next_retry_time - time.time())
