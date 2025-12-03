"""
Timing utilities - delays, waits, retries.
"""

import random
import time
from collections.abc import Callable
from typing import Any, Tuple

import shadowlib.globals as globals


def currentTime() -> float:
    """
    Get the current time in seconds since the epoch.

    Returns:
        Current time in seconds
    """
    return time.time()


def currentTick() -> int:
    """
    Get the current tick count from the game client.

    Returns:
        Current tick count as an integer
    """
    client = globals.getClient()
    return client.cache["tick"]


def waitTicks(ticks: int, tickDuration: float = 0.6):
    """
    Wait for a specified number of game ticks.

    Args:
        ticks: Number of ticks to wait
        tickDuration: Duration of a single tick in seconds (default 0.6s)
    """
    start_tick = currentTick()
    while currentTick() - start_tick < ticks:
        time.sleep(0.01)


def sleep(min_seconds: float, max_seconds: float | None = None):
    """
    Sleep for a random duration between min and max seconds.
    If max not provided, sleeps for exactly min_seconds.

    Args:
        min_seconds: Minimum sleep time
        max_seconds: Maximum sleep time (optional)

    Example:
        timing.sleep(1, 2)  # Sleep 1-2 seconds
        timing.sleep(0.5)   # Sleep exactly 0.5 seconds
    """
    if max_seconds is None:
        time.sleep(min_seconds)
    else:
        duration = random.uniform(min_seconds, max_seconds)
        time.sleep(duration)


def waitUntil(
    condition: Callable[[], bool], timeout: float = 10.0, poll_interval: float = 0.1
) -> bool:
    """
    Wait until a condition becomes true or timeout occurs.

    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: How often to check condition in seconds

    Returns:
        True if condition was met, False if timeout

    Example:
        def is_bank_open():
            return banking.is_open()

        if timing.wait_until(is_bank_open, timeout=5):
            print("Bank opened!")
        else:
            print("Timeout waiting for bank")
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(poll_interval)

    return False


def retry(
    func: Callable[[], Any],
    max_attempts: int = 3,
    delay: float = 1.0,
    exponential_backoff: bool = False,
) -> Any | None:
    """
    Retry a function multiple times if it fails.

    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        exponential_backoff: If True, delay doubles each attempt

    Returns:
        Function result if successful, None if all attempts failed

    Example:
        def open_bank():
            if banking.open_nearest():
                return True
            raise Exception("Failed to open bank")

        result = timing.retry(open_bank, max_attempts=3, delay=2)
    """
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"All {max_attempts} attempts failed: {e}")
                return None

            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
            time.sleep(current_delay)

            if exponential_backoff:
                current_delay *= 2

    return None


def measureTime(func: Callable[[], Any]) -> Tuple[Any, float]:
    """
    Measure execution time of a function.

    Args:
        func: Function to measure

    Returns:
        Tuple of (result, elapsed_time_seconds)

    Example:
        result, elapsed = timing.measureTime(lambda: inventory.get_items())
        print(f"Function took {elapsed:.3f} seconds")
    """
    start = time.time()
    result = func()
    elapsed = time.time() - start
    return result, elapsed
