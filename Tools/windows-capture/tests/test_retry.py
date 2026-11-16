"""Unit tests for exponential backoff, jitter, and Retry-After header parsing."""

import email.utils
import time
import unittest
from datetime import datetime, timedelta, timezone

from noop_agent.sync.retry import BackoffManager, calculate_backoff, parse_retry_after


class TestRetry(unittest.TestCase):
    """Test suite for retry and backoff calculations."""

    def test_parse_retry_after_integer_seconds(self):
        self.assertEqual(parse_retry_after("60"), 60.0)
        self.assertEqual(parse_retry_after("  120  "), 120.0)
        self.assertEqual(parse_retry_after("0"), 0.0)

    def test_parse_retry_after_http_date(self):
        target = datetime.now(timezone.utc) + timedelta(seconds=45)
        http_date_str = email.utils.format_datetime(target)
        parsed = parse_retry_after(http_date_str)
        self.assertIsNotNone(parsed)
        self.assertGreater(parsed, 35.0)
        self.assertLessEqual(parsed, 50.0)

    def test_parse_retry_after_invalid_and_none(self):
        self.assertIsNone(parse_retry_after(None))
        self.assertIsNone(parse_retry_after(""))
        self.assertIsNone(parse_retry_after("not-a-number-or-date"))

    def test_calculate_backoff_bounds(self):
        base = 2.0
        max_d = 30.0
        # No jitter
        self.assertEqual(calculate_backoff(attempt=0, base_delay=base, max_delay=max_d, jitter=False), 2.0)
        self.assertEqual(calculate_backoff(attempt=1, base_delay=base, max_delay=max_d, jitter=False), 4.0)
        self.assertEqual(calculate_backoff(attempt=2, base_delay=base, max_delay=max_d, jitter=False), 8.0)
        self.assertEqual(calculate_backoff(attempt=5, base_delay=base, max_delay=max_d, jitter=False), 30.0)

        # With jitter, delay should always be within [0, ceiling]
        for attempt in range(6):
            delay = calculate_backoff(attempt=attempt, base_delay=base, max_delay=max_d, jitter=True)
            ceiling = min(max_d, base * (2.0 ** attempt))
            self.assertGreaterEqual(delay, 0.0)
            self.assertLessEqual(delay, ceiling)

    def test_backoff_manager_lifecycle(self):
        mgr = BackoffManager(base_delay=1.0, max_delay=10.0, factor=2.0)
        self.assertEqual(mgr.attempt, 0)
        self.assertEqual(mgr.consecutive_failures, 0)
        self.assertTrue(mgr.can_retry_now)

        # Failure 1
        d1 = mgr.record_failure()
        self.assertEqual(mgr.attempt, 1)
        self.assertEqual(mgr.consecutive_failures, 1)
        self.assertLessEqual(d1, 1.0)

        # Respect Retry-After
        d_explicit = mgr.record_failure(retry_after=5.0)
        self.assertEqual(d_explicit, 5.0)
        self.assertEqual(mgr.attempt, 2)
        self.assertEqual(mgr.consecutive_failures, 2)

        # Success resets
        mgr.record_success()
        self.assertEqual(mgr.attempt, 0)
        self.assertEqual(mgr.consecutive_failures, 0)
        self.assertTrue(mgr.can_retry_now)


if __name__ == "__main__":
    unittest.main()
