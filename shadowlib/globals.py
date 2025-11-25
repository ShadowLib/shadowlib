"""
Global API and Client instances for convenient access.

This module provides singleton access to the RuneLite API and Client instances,
allowing modules to work without explicit client passing while still supporting
dependency injection for testing.

Usage patterns:

1. Simple scripts (using globals):
    from shadowlib.tabs.inventory import getItems
    items = getItems()  # Uses global client automatically

2. Advanced (explicit client):
    from shadowlib import Client
    client = Client()
    items = client.getInventory().getItems()

3. Module implementation (hybrid approach):
    from shadowlib.globals import getClient

    class Inventory:
        def __init__(self, client=None):
            self.client = client or getClient()  # Use passed OR global
"""

from shadowlib._internal.api import RuneLiteAPI

# Global instances
_global_api: RuneLiteAPI | None = None
_global_client = None  # Forward reference, actual Client class imported later
_resources_checked = False  # Track if we've checked resources this session


def _checkResourceUpdates():
    """
    Check for game resource updates (varps, objects).

    Only checks once per session. Downloads and loads resources if needed.
    """
    global _resources_checked

    if _resources_checked:
        return

    try:
        from shadowlib._internal.cache_manager import ensureResourcesLoaded

        # Download and load resources (handles version checking internally)
        if not ensureResourcesLoaded():
            print("⚠️  Some resources failed to load")

        _resources_checked = True

    except Exception as e:
        # Don't fail client init if resource check fails
        print(f"⚠️  Resource loading failed: {e}")
        import traceback

        traceback.print_exc()
        _resources_checked = True  # Mark as checked to avoid retry spam


def getApi() -> RuneLiteAPI:
    """
    Get or create the global RuneLite API instance.

    The API is automatically connected on first access.

    Returns:
        RuneLiteAPI: The global API instance

    Example:
        api = getApi()
        query = api.query()
    """
    global _global_api

    if _global_api is None:
        print("🔗 Creating global API instance...")
        _global_api = RuneLiteAPI()
        _global_api.connect()
        print("✅ Global API connected")

        # Register for cleanup
        from shadowlib._internal.cleanup import ensureCleanupOnSignal, registerApiForCleanup

        registerApiForCleanup(_global_api)
        ensureCleanupOnSignal()

    return _global_api


def getClient():
    """
    Get or create the global Client instance.

    The client wraps the global API and provides high-level access to all
    game modules (inventory, bank, skills, etc).

    On first call, checks for updates to both RuneLite API (via getApi())
    and game resources (varps, objects).

    Returns:
        Client: The global client instance

    Example:
        client = getClient()
        items = client.getInventory().getItems()
    """
    global _global_client

    if _global_client is None:
        # Import here to avoid circular dependency
        from shadowlib.client import Client

        print("🎮 Creating global Client instance...")
        api = getApi()  # Reuse global API (checks RuneLite API updates)

        # Check for game resource updates
        _checkResourceUpdates()

        _global_client = Client(api=api)
        print("✅ Global Client ready")

    return _global_client


def setApi(api: RuneLiteAPI) -> None:
    """
    Override the global API instance.

    Useful for testing or advanced scenarios where you need
    to inject a custom API implementation.

    Args:
        api: Custom RuneLiteAPI instance

    Example:
        from shadowlib.globals import setApi
        setApi(MockAPI())  # Use mock for testing
    """
    global _global_api
    _global_api = api


def setClient(client) -> None:
    """
    Override the global Client instance.

    Useful for testing or advanced scenarios where you need
    to inject a custom client implementation.

    Args:
        client: Custom Client instance

    Example:
        from shadowlib.globals import setClient
        setClient(MockClient())  # Use mock for testing
    """
    global _global_client
    _global_client = client


def resetGlobals() -> None:
    """
    Reset global instances to None.

    Useful for testing to ensure clean state between tests.

    Example:
        from shadowlib.globals import resetGlobals

        def testSomething():
            resetGlobals()  # Start fresh
            # ... test code ...
    """
    global _global_api, _global_client, _resources_checked
    _global_api = None
    _global_client = None
    _resources_checked = False


# Convenience exports
__all__ = [
    "getApi",
    "getClient",
    "setApi",
    "setClient",
    "resetGlobals",
]
