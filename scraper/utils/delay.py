"""
Delay utilities for polite web scraping

Provides functions for implementing polite delays between requests
and adaptive backoff strategies for handling failures.
"""

import random
import time


def polite_delay(min_seconds: float = 3.0, max_seconds: float = 8.0) -> None:
    """
    Implement a polite delay between requests.

    Args:
        min_seconds: Minimum delay in seconds (default: 3.0)
        max_seconds: Maximum delay in seconds (default: 8.0)
    """
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def adaptive_delay(
    base_delay: float = 3.0,
    max_delay: float = 15.0,
    backoff_factor: float = 1.5,
    consecutive_failures: int = 0,
) -> float:
    """
    Calculate adaptive delay based on consecutive failures.

    Args:
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for each failure
        consecutive_failures: Number of consecutive failures

    Returns:
        Calculated delay in seconds
    """
    if consecutive_failures == 0:
        return base_delay

    delay = base_delay * (backoff_factor**consecutive_failures)
    return min(delay, max_delay)


def exponential_backoff(
    attempt: int, base_delay: float = 1.0, max_delay: float = 60.0
) -> float:
    """
    Calculate exponential backoff delay for retry attempts.

    Args:
        attempt: Current attempt number (1-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Calculated delay in seconds
    """
    delay = base_delay * (2 ** (attempt - 1))
    return min(delay, max_delay)
