"""
Main Client class - singleton that provides access to all game modules.
"""

from typing import TYPE_CHECKING

from shadowlib._internal.api import RuneLiteAPI
from shadowlib.generated.constants.varclient import VarClientStr

if TYPE_CHECKING:
    from shadowlib._internal.cache.event_cache import EventCache
    from shadowlib.generated.constants.animation_id import AnimationID
    from shadowlib.generated.constants.interface_id import InterfaceID
    from shadowlib.generated.constants.item_id import ItemID
    from shadowlib.generated.constants.npc_id import NpcID
    from shadowlib.generated.constants.object_id import ObjectID
    from shadowlib.generated.constants.varclient_id import VarClientID
    from shadowlib.input import Input
    from shadowlib.interactions import Interactions
    from shadowlib.interfaces import Interfaces
    from shadowlib.navigation import Navigation
    from shadowlib.player import Player
    from shadowlib.tabs import Tabs
    from shadowlib.world import World


class Client:
    """
    Singleton client providing access to all game modules.

    Example:
        from shadowlib.client import client

        items = client.tabs.inventory.getItems()
        client.interfaces.bank.depositAll()
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """Actual initialization, runs once."""
        from shadowlib._internal.cache_manager import ensureResourcesLoaded

        print("🎮 Initializing Client...")

        # Initialize API
        self.api = RuneLiteAPI()
        self.api.connect()

        # Check for game resource updates
        if not ensureResourcesLoaded():
            print("⚠️  Some resources failed to load")

        self._connected = True

        # Pre-import constants that the consumer thread needs during warmup.
        # This prevents deadlock: if we don't import these now, the background
        # thread will try to import them while we hold the import lock.
        import contextlib

        with contextlib.suppress(ImportError):
            from shadowlib.generated.constants.varclient_id import VarClientID  # noqa: F401

        # Initialize event cache and consumer immediately
        from shadowlib._internal.cache.event_cache import EventCache
        from shadowlib._internal.events.consumer import EventConsumer

        self._event_cache = EventCache(event_history_size=100)
        self._event_consumer = EventConsumer(self._event_cache, warn_on_gaps=False)
        # Start consumer and wait for warmup - safe now that constants are pre-imported
        self._event_consumer.start(wait_for_warmup=True)

        # Register for automatic cleanup on exit
        from shadowlib._internal.cleanup import registerApiForCleanup

        registerApiForCleanup(self.api)

        # Ensure cleanup happens on Ctrl+C
        from shadowlib._internal.cleanup import ensureCleanupOnSignal

        ensureCleanupOnSignal()

        print("✅ Client ready")

    def waitForWarmup(self, timeout: float = 5.0) -> bool:
        """
        Wait for event cache warmup to complete.

        Call this after importing if you need to ensure the cache is populated
        before proceeding. The warmup processes all existing events in /dev/shm.

        Args:
            timeout: Maximum seconds to wait for warmup

        Returns:
            True if warmup completed, False if timeout

        Example:
            from shadowlib.client import client
            client.waitForWarmup()  # Ensure cache is ready
            items = client.tabs.inventory.getItems()
        """
        if self._event_consumer is None:
            return True
        return self._event_consumer.waitForWarmup(timeout=timeout)

    def connect(self):
        """Connect to RuneLite bridge."""
        if not self._connected:
            print("🔗 Connecting client to RuneLite...")
            self.api.connect()
            self._connected = True
            print("✅ Client connected!")

    def disconnect(self):
        """Disconnect from RuneLite bridge and cleanup resources."""
        if self._connected:
            print("🔌 Disconnecting client...")

            # Stop event consumer if running
            if self._event_consumer is not None:
                self._event_consumer.stop()
                self._event_consumer = None

            self._connected = False
            print("✅ Client disconnected")

    def isConnected(self) -> bool:
        """
        Check if client is connected.

        Returns:
            bool: Connection status
        """
        return self._connected

    def query(self):
        """
        Create a new query builder.

        Returns:
            Query builder instance
        """
        return self.api.query()

    @property
    def event_cache(self) -> "EventCache":
        """
        Get event cache instance.

        Provides access to cached game state from events.

        Returns:
            EventCache instance

        Example:
            >>> age = client.event_cache.getAge()
            >>> inventory = client.event_cache.getInventory()
        """
        return self._event_cache

    @property
    def ItemID(self) -> type["ItemID"]:
        """Access ItemID constants."""
        try:
            from .generated.constants import ItemID

            return ItemID
        except ImportError:
            from constants import ItemID

            return ItemID

    @property
    def ObjectID(self) -> type["ObjectID"]:
        """Access ObjectID constants."""
        try:
            from .generated.constants import ObjectID

            return ObjectID
        except ImportError:
            from constants import ObjectID

            return ObjectID

    @property
    def NpcID(self) -> type["NpcID"]:
        """Access NpcID constants."""
        try:
            from .generated.constants import NpcID

            return NpcID
        except ImportError:
            from constants import NpcID

            return NpcID

    @property
    def AnimationID(self) -> type["AnimationID"]:
        """Access AnimationID constants."""
        try:
            from .generated.constants import AnimationID

            return AnimationID
        except ImportError:
            from constants import AnimationID

            return AnimationID

    @property
    def InterfaceID(self) -> type["InterfaceID"]:
        """Access InterfaceID constants."""
        try:
            from .generated.constants import InterfaceID

            return InterfaceID
        except ImportError:
            from constants import InterfaceID

            return InterfaceID

    @property
    def VarClientID(self) -> type["VarClientID"]:
        """Access VarClientID constants."""
        try:
            from .generated.constants import VarClientID

            return VarClientID
        except ImportError:
            from constants import VarClientID

            return VarClientID

    # Namespace properties - return singleton instances
    @property
    def tabs(self) -> "Tabs":
        """
        Get tabs namespace.

        Returns:
            Tabs namespace with all game tabs

        Example:
            >>> items = client.tabs.inventory.getItems()
            >>> skills = client.tabs.skills.getAllSkills()
            >>> client.tabs.prayer.activatePrayer("Protect from Melee")
        """
        from shadowlib.tabs import tabs

        return tabs

    @property
    def input(self) -> "Input":
        """
        Get input namespace.

        Returns:
            Input namespace with mouse, keyboard, etc.

        Example:
            >>> client.input.mouse.leftClick(100, 200)
            >>> client.input.keyboard.type("Hello")
        """
        from shadowlib.input import input

        return input

    @property
    def world(self) -> "World":
        """
        Get world namespace.

        Returns:
            World namespace with 3D entities

        Example:
            >>> items = client.world.groundItems.getAllItems()
            >>> npcs = client.world.npcs.getNearby()
        """
        from shadowlib.world import world

        return world

    @property
    def navigation(self) -> "Navigation":
        """
        Get navigation namespace.

        Returns:
            Navigation namespace with pathfinding, walking, etc.

        Example:
            >>> path = client.navigation.pathfinder.getPath(3200, 3200, 0)
            >>> client.navigation.walker.walkTo(3200, 3200)
        """
        from shadowlib.navigation import navigation

        return navigation

    @property
    def interactions(self) -> "Interactions":
        """
        Get interactions namespace.

        Returns:
            Interactions namespace with menu, widgets, etc.

        Example:
            >>> client.interactions.menu.clickOption("Attack")
            >>> client.interactions.widgets.click(10551297)
        """
        from shadowlib.interactions import interactions

        return interactions

    @property
    def interfaces(self) -> "Interfaces":
        """
        Get interfaces namespace.

        Returns:
            Interfaces namespace with bank, GE, shop, etc.

        Example:
            >>> client.interfaces.bank.depositAll()
            >>> client.interfaces.grand_exchange.sell(995, 1000, 100)
        """
        from shadowlib.interfaces import interfaces

        return interfaces

    @property
    def player(self) -> "Player":
        """
        Get player accessor.

        Returns:
            Player instance

        Example:
            >>> pos = client.player.position
            >>> energy = client.player.energy
            >>> distance = client.player.distanceTo(3200, 3200)
        """
        from shadowlib.player.player import player

        return player

    # Resources namespace
    @property
    def resources(self):
        """
        Access game resources (varps, objects).

        Returns:
            ResourcesNamespace with .varps and .objects

        Example:
            >>> quest_points = client.resources.varps.getVarpByName("quest_points")
            >>> tree = client.resources.objects.getById(1276)
        """
        if not hasattr(self, "_resources_namespace"):
            self._resources_namespace = self._ResourcesNamespace()
        return self._resources_namespace

    class _ResourcesNamespace:
        """Namespace for accessing game resources."""

        @property
        def varps(self):
            """Access varps/varbits functions."""
            from shadowlib._internal.resources import varps

            return varps

        @property
        def objects(self):
            """Access objects functions."""
            from shadowlib._internal.resources import objects

            return objects

    @property
    def cache(self) -> "EventCache":
        """
        Event cache with instant access to game state and events.

        The event consumer is started automatically on Client initialization
        and watches /dev/shm/runelite_doorbell using inotify with zero CPU
        usage when idle.

        Returns:
            EventCache instance with game state and event history

        Example:
            # Access latest gametick state
            tick = client.cache.tick
            energy = client.cache.energy
            pos = client.cache.position

            # Access derived state
            inventory = client.cache.getInventory()
            varp = client.cache.getVarp(173)

            # Access recent events
            recent_chats = client.cache.getRecentEvents('chat_message', n=10)
            for chat in recent_chats:
                print(chat)

            # Check data freshness
            if client.cache.isFresh():
                print(f"Data is fresh (age: {client.cache.getAge():.2f}s)")
        """
        return self._event_cache

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.disconnect()


# Module-level singleton instance
client = Client()
