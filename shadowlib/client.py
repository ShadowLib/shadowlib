"""
Main Client class for advanced users who want explicit control.
Most users won't need this - they can use the module-level functions directly.
"""

from shadowlib._internal.api import RuneLiteAPI


class Client:
    """
    Advanced client for explicit API management.

    Most users should use the module-level functions (inventory.getItems(), etc)
    which use a global auto-connected API. Use this Client class if you need:
    - Multiple API instances
    - Explicit connection management
    - Custom API configuration

    Example:
        client = Client()
        client.connect()

        items = client.getInventory().getItems()
        client.getBank().depositAll()
    """

    def __init__(self, api: RuneLiteAPI | None = None):
        """
        Initialize client with optional custom API instance.

        Args:
            api: Optional RuneLiteAPI instance. If None, uses global API.
        """
        if api is None:
            from shadowlib.globals import getApi

            self.api = getApi()
        else:
            self.api = api

        # If we got an API (global or passed), assume it's connected
        # Users should call connect() explicitly if using a fresh API
        self._connected = True

        # Lazy-load namespace controllers
        self._tabs = None
        self._input = None
        self._world = None
        self._navigation = None
        self._interactions = None
        self._interfaces = None
        self._player = None

        # Initialize event cache and consumer immediately
        from shadowlib._internal.cache.event_cache import EventCache
        from shadowlib._internal.events.consumer import EventConsumer

        self._event_cache = EventCache(event_history_size=100)
        self._event_consumer = EventConsumer(self._event_cache, warn_on_gaps=False)
        self._event_consumer.start()

        # Register for automatic cleanup on exit
        from shadowlib._internal.cleanup import registerApiForCleanup

        registerApiForCleanup(self.api)

        # Ensure cleanup happens on Ctrl+C
        from shadowlib._internal.cleanup import ensureCleanupOnSignal

        ensureCleanupOnSignal()

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
    def event_cache(self):
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
    def ItemID(self):
        """Access ItemID constants."""
        try:
            from .generated.constants import ItemID

            return ItemID
        except ImportError:
            from constants import ItemID

            return ItemID

    @property
    def ObjectID(self):
        """Access ObjectID constants."""
        try:
            from .generated.constants import ObjectID

            return ObjectID
        except ImportError:
            from constants import ObjectID

            return ObjectID

    @property
    def NpcID(self):
        """Access NpcID constants."""
        try:
            from .generated.constants import NpcID

            return NpcID
        except ImportError:
            from constants import NpcID

            return NpcID

    @property
    def AnimationID(self):
        """Access AnimationID constants."""
        try:
            from .generated.constants import AnimationID

            return AnimationID
        except ImportError:
            from constants import AnimationID

            return AnimationID

    @property
    def InterfaceID(self):
        """Access InterfaceID constants."""
        try:
            from .generated.constants import InterfaceID

            return InterfaceID
        except ImportError:
            from constants import InterfaceID

            return InterfaceID

    @property
    def VarClientInt(self):
        """Access VarClientInt constants."""
        try:
            from .generated.constants import VarClientInt

            return VarClientInt
        except ImportError:
            from constants import VarClientInt

            return VarClientInt

    @property
    def VarClientStr(self):
        """Access VarClientStr constants."""
        try:
            from .generated.constants import VarClientStr

            return VarClientStr
        except ImportError:
            from constants import VarClientStr

            return VarClientStr

    # Namespace properties
    @property
    def tabs(self):
        """
        Get tabs namespace.

        Returns:
            Tabs namespace with all game tabs

        Example:
            >>> items = client.tabs.inventory.getItems()
            >>> skills = client.tabs.skills.getAllSkills()
            >>> client.tabs.prayer.activatePrayer("Protect from Melee")
        """
        if self._tabs is None:
            from shadowlib.tabs import Tabs

            self._tabs = Tabs(self)
        return self._tabs

    @property
    def input(self):
        """
        Get input namespace.

        Returns:
            Input namespace with mouse, keyboard, etc.

        Example:
            >>> client.input.mouse.leftClick(100, 200)
            >>> client.input.keyboard.type("Hello")
        """
        if self._input is None:
            from shadowlib.input import Input

            self._input = Input(self)
        return self._input

    @property
    def world(self):
        """
        Get world namespace.

        Returns:
            World namespace with 3D entities

        Example:
            >>> items = client.world.ground_items.getAllItems()
            >>> npcs = client.world.npcs.getNearby()
        """
        if self._world is None:
            from shadowlib.world import World

            self._world = World(self)
        return self._world

    @property
    def navigation(self):
        """
        Get navigation namespace.

        Returns:
            Navigation namespace with pathfinding, walking, etc.

        Example:
            >>> path = client.navigation.pathfinder.getPath(3200, 3200, 0)
            >>> client.navigation.walker.walkTo(3200, 3200)
        """
        if self._navigation is None:
            from shadowlib.navigation import Navigation

            self._navigation = Navigation(self)
        return self._navigation

    @property
    def interactions(self):
        """
        Get interactions namespace.

        Returns:
            Interactions namespace with menu, widgets, etc.

        Example:
            >>> client.interactions.menu.clickOption("Attack")
            >>> client.interactions.widgets.click(10551297)
        """
        if self._interactions is None:
            from shadowlib.interactions import Interactions

            self._interactions = Interactions(self)
        return self._interactions

    @property
    def interfaces(self):
        """
        Get interfaces namespace.

        Returns:
            Interfaces namespace with bank, GE, shop, etc.

        Example:
            >>> client.interfaces.bank.depositAll()
            >>> client.interfaces.grand_exchange.sell(995, 1000, 100)
        """
        if self._interfaces is None:
            from shadowlib.interfaces import Interfaces

            self._interfaces = Interfaces(self)
        return self._interfaces

    @property
    def player(self):
        """
        Get player accessor.

        Returns:
            Player instance

        Example:
            >>> pos = client.player.position
            >>> energy = client.player.energy
            >>> distance = client.player.distanceTo(3200, 3200)
        """
        if self._player is None:
            from shadowlib.player import Player

            self._player = Player(self)
        return self._player

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
    def cache(self):
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
