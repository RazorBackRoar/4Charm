"""Retry and adaptive rate-limit policy for the scraper.

Encapsulates:
  - Exponential backoff with jitter for failed downloads
  - Adaptive rate-limit delay that grows on failure and shrinks on success

The policy is stateful (current_delay) so a single RetryPolicy instance is
created per scraper. Tests construct their own RetryPolicy to exercise the
math without standing up a full FourChanScraper.
"""

from __future__ import annotations

import random
import time

import four_charm.config as config


class RetryPolicy:
    """Exponential backoff with jitter plus an adaptive rate-limit window."""

    def __init__(
        self,
        *,
        base_delay: float | None = None,
        max_delay: float | None = None,
        backoff_multiplier: float | None = None,
        base_retry_delay: float | None = None,
        max_retry_delay: float | None = None,
    ) -> None:
        self.base_delay = base_delay if base_delay is not None else config.BASE_DELAY
        self.max_delay = max_delay if max_delay is not None else config.MAX_DELAY
        self.backoff_multiplier = (
            backoff_multiplier
            if backoff_multiplier is not None
            else config.BACKOFF_MULTIPLIER
        )
        self.base_retry_delay = (
            base_retry_delay
            if base_retry_delay is not None
            else config.BASE_RETRY_DELAY
        )
        self.max_retry_delay = (
            max_retry_delay
            if max_retry_delay is not None
            else config.MAX_RETRY_DELAY
        )
        self.current_delay: float = self.base_delay

    def calculate_retry_delay(
        self, attempt: int, base_delay: float | None = None
    ) -> float:
        """Exponential backoff capped at ``max_retry_delay`` plus 0-1s jitter.

        Args:
            attempt: Retry attempt number (0-indexed).
            base_delay: Override the configured base delay in seconds.

        Returns:
            Delay in seconds with jitter applied.
        """
        base = base_delay if base_delay is not None else self.base_retry_delay
        exponential_delay = (2**attempt) * base
        capped_delay = min(exponential_delay, self.max_retry_delay)
        jitter = random.uniform(0, 1)
        return capped_delay + jitter

    def adaptive_delay(self, success: bool = True) -> None:
        """Tune ``current_delay`` based on the most recent request outcome.

        On success the delay shrinks (divided by ``backoff_multiplier``);
        on failure it grows (multiplied) up to ``max_delay``. Always sleeps
        ``current_delay`` seconds so the rate-limit window is honoured even
        on the happy path.
        """
        if success:
            self.current_delay = max(self.base_delay, self.current_delay / 1.1)
        else:
            self.current_delay = min(
                self.max_delay, self.current_delay * self.backoff_multiplier
            )
        time.sleep(self.current_delay)
