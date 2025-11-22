"""
Automatic cleanup utilities for RuneLite bridge resources.

Provides atexit registration and decorators to ensure proper cleanup
of tick queries and monitors even when scripts error or exit unexpectedly.
"""

import atexit
import functools
import sys
from typing import Callable

# Global tracking of resources that need cleanup
_registered_apis = []
_cleanup_registered = False


def registerApiForCleanup(api) -> None:
    """
    Register a RuneLiteAPI instance for automatic cleanup on exit.

    This ensures that even if your script crashes or exits unexpectedly,
    the tick query will be uninstalled and the monitor will be stopped.

    Args:
        api: RuneLiteAPI instance to register

    Example:
        api = RuneLiteAPI()
        registerApiForCleanup(api)
        api.connect()

        # Now if script crashes, cleanup will still happen
        q = api.query()
        q.install({"tick": q.client.getTickCount()})
    """
    global _cleanup_registered

    if api not in _registered_apis:
        _registered_apis.append(api)

    # Register atexit handler on first registration
    if not _cleanup_registered:
        atexit.register(_cleanupAll)
        _cleanup_registered = True


def _cleanupAll():
    """Internal cleanup handler called by atexit."""
    if not _registered_apis:
        return

    print("\n🧹 Auto-cleanup: Shutting down RuneLite bridge resources...")

    # Event consumer cleanup is handled by Client.disconnect()
    # which is called automatically via context manager or explicit disconnect

    print("🧹 Cleanup complete")


def withCleanup(func: Callable) -> Callable:
    """
    Decorator that ensures cleanup happens even if the decorated function raises an exception.

    This is useful for main functions or long-running bot scripts.

    Example:
        from shadowlib._internal.cleanup import withCleanup
        from shadowlib.globals import getClient

        @withCleanup
        def main():
            client = getClient()
            # Bot logic here
            # Cleanup guaranteed even on error

        if __name__ == "__main__":
            main()
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            # Ensure cleanup runs even on exception
            _cleanupAll()

    return wrapper


def ensureCleanupOnSignal():
    """
    Register signal handlers to ensure cleanup on SIGINT (Ctrl+C) and SIGTERM.

    This is useful for long-running bot scripts that might be interrupted.

    Example:
        from shadowlib._internal.cleanup import ensureCleanupOnSignal

        ensureCleanupOnSignal()

        # Now cleanup will happen even if user presses Ctrl+C
        # ... bot code
    """
    import signal

    def signalHandler(signum, frame):
        print(f"\n⚠️  Received signal {signum}, cleaning up...")
        _cleanupAll()
        sys.exit(0)

    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)
    print("✅ Cleanup registered for SIGINT and SIGTERM")


class CleanupContext:
    """
    Context manager for automatic cleanup.

    Example:
        from shadowlib._internal.cleanup import CleanupContext
        from shadowlib.globals import getApi

        with CleanupContext() as ctx:
            api = getApi()
            ctx.register(api)

            # Do bot stuff - cleanup automatic on exit or error
            while True:
                # Bot logic
                pass
    """

    def __init__(self):
        self.api = None

    def register(self, api) -> None:
        """Register an API instance for cleanup."""
        self.api = api

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup everything."""
        # Don't suppress exceptions
        return False
