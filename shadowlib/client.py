"""
Main Client class for advanced users who want explicit control.
Most users won't need this - they can use the module-level functions directly.
"""

from typing import Optional

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

    def __init__(self, api: Optional[RuneLiteAPI] = None):
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

        # Lazy-load interface modules
        self._bank = None
        self._interfaces = None

        # Lazy-load world modules
        self._player = None
        self._world = None

        # Lazy-load interaction modules
        self._menu = None

        # Lazy-load tab modules
        self._gametabs = None
        self._combat = None
        self._skills = None
        self._progress = None
        self._inventory = None
        self._equipment = None
        self._prayer = None
        self._magic = None
        self._grouping = None
        self._friends = None
        self._account = None
        self._settings = None
        self._logout = None
        self._emotes = None
        self._music = None

        # Lazy-load utility modules
        self._timing = None
        self._math = None
        self._geometry = None
        self._random = None

        # Lazy-load world entity factories
        self._rsobjects = None
        self._rsnpcs = None
        self._ground_items = None

        # Lazy-load IO instance
        self._io = None

        # Lazy-load navigation
        self._pathfinder = None

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

    # Interface modules
    def getBank(self):
        """Get bank module."""
        if self._bank is None:
            from shadowlib.interfaces.bank import Bank

            self._bank = Bank(self)
        return self._bank

    def getInterfaces(self):
        """Get interfaces module."""
        if self._interfaces is None:
            from shadowlib.interfaces import Interfaces

            self._interfaces = Interfaces(self)
        return self._interfaces

    # World modules
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

    def getPlayer(self):
        """Get player module (deprecated - use client.player)."""
        return self.player

    def getWorld(self):
        """Get world module."""
        if self._world is None:
            from shadowlib.world import World

            self._world = World(self)
        return self._world

    # Interaction modules
    def getMenu(self):
        """Get menu module for right-click context menu interactions."""
        if self._menu is None:
            from shadowlib.interactions.menu import Menu

            self._menu = Menu(self)
        return self._menu

    # Tab modules
    def getGameTabs(self):
        """
        Get generic GameTabs interface for tab management.

        Provides access to base GameTabs functionality like checking
        which tab is currently open.

        Example:
            # Get currently open tab
            current = client.getGameTabs().getOpenTab()

            # Check if specific tab is open
            if client.getGameTabs().isOpen():
                print("A tab is open")
        """
        if self._gametabs is None:
            from shadowlib.tabs.gametab import GameTabs

            self._gametabs = GameTabs(self)
        return self._gametabs

    def getCombat(self):
        """Get Combat game tab."""
        if self._combat is None:
            from shadowlib.tabs.combat import Combat

            self._combat = Combat(self)
        return self._combat

    def getSkills(self):
        """Get Skills game tab."""
        if self._skills is None:
            from shadowlib.tabs.skills import Skills

            self._skills = Skills(self)
        return self._skills

    def getProgress(self):
        """Get Progress game tab (Quests/Achievements)."""
        if self._progress is None:
            from shadowlib.tabs.progress import Progress

            self._progress = Progress(self)
        return self._progress

    def getInventory(self):
        """Get Inventory game tab."""
        if self._inventory is None:
            from shadowlib.tabs.inventory import Inventory

            self._inventory = Inventory(self)
        return self._inventory

    def getEquipment(self):
        """Get Equipment game tab."""
        if self._equipment is None:
            from shadowlib.tabs.equipment import Equipment

            self._equipment = Equipment(self)
        return self._equipment

    def getPrayer(self):
        """Get Prayer game tab."""
        if self._prayer is None:
            from shadowlib.tabs.prayer import Prayer

            self._prayer = Prayer(self)
        return self._prayer

    def getMagic(self):
        """Get Magic game tab."""
        if self._magic is None:
            from shadowlib.tabs.magic import Magic

            self._magic = Magic(self)
        return self._magic

    def getGrouping(self):
        """Get Grouping game tab (Clan/Group activities)."""
        if self._grouping is None:
            from shadowlib.tabs.grouping import Grouping

            self._grouping = Grouping(self)
        return self._grouping

    def getFriends(self):
        """Get Friends game tab."""
        if self._friends is None:
            from shadowlib.tabs.friends import Friends

            self._friends = Friends(self)
        return self._friends

    def getAccount(self):
        """Get Account Management game tab."""
        if self._account is None:
            from shadowlib.tabs.account import Account

            self._account = Account(self)
        return self._account

    def getSettings(self):
        """Get Settings game tab."""
        if self._settings is None:
            from shadowlib.tabs.settings import Settings

            self._settings = Settings(self)
        return self._settings

    def getLogout(self):
        """Get Logout game tab."""
        if self._logout is None:
            from shadowlib.tabs.logout import Logout

            self._logout = Logout(self)
        return self._logout

    def getEmotes(self):
        """Get Emotes game tab."""
        if self._emotes is None:
            from shadowlib.tabs.emotes import Emotes

            self._emotes = Emotes(self)
        return self._emotes

    def getMusic(self):
        """Get Music game tab."""
        if self._music is None:
            from shadowlib.tabs.music import Music

            self._music = Music(self)
        return self._music

    # Resources
    def getVarps(self):
        """Get varps/varbits resource manager."""
        from shadowlib.resources import varps

        return varps

    def getObjects(self):
        """Get objects resource manager."""
        from shadowlib.resources import objects

        return objects

    # Utility modules
    def getTiming(self):
        """Get timing utilities."""
        if self._timing is None:
            from shadowlib import utils

            self._timing = utils.timing
        return self._timing

    def getMath(self):
        """Get math utilities."""
        if self._math is None:
            from shadowlib import utils

            self._math = utils.math
        return self._math

    def getGeometry(self):
        """Get geometry utilities."""
        if self._geometry is None:
            from shadowlib import utils

            self._geometry = utils.geometry
        return self._geometry

    def getRandom(self):
        """Get random utilities."""
        if self._random is None:
            from shadowlib import utils

            self._random = utils.random
        return self._random

    # World entity factories
    def getRSObjects(self):
        """
        Get RSObject factory for creating and interacting with game objects.

        Returns:
            RSObjectFactory instance

        Example:
            tree = client.getRSObjects().create("Tree", 1278, (3209, 3221, 0))
            tree.click()
        """
        if self._rsobjects is None:
            from shadowlib.world.rsobject import RSObjectFactory

            self._rsobjects = RSObjectFactory(self)
        return self._rsobjects

    def getRSNPCs(self):
        """
        Get RSNPC factory for creating and interacting with NPCs.

        Returns:
            RSNPCFactory instance

        Example:
            goblin = client.getRSNPCs().create(name="Goblin", npcId=3029, coord=(3243, 3245, 0))
            goblin.click()
        """
        if self._rsnpcs is None:
            from shadowlib.world.rsnpc import RSNPCFactory

            self._rsnpcs = RSNPCFactory(self)
        return self._rsnpcs

    def getGroundItems(self):
        """
        Get ground items accessor.

        Returns:
            GroundItems instance

        Example:
            # Get all items
            items = client.getGroundItems().getAllItems()

            # Find coins
            coins = client.getGroundItems().findItemsById(995)
        """
        if self._ground_items is None:
            from shadowlib.world.ground_items import GroundItems

            self._ground_items = GroundItems(self)
        return self._ground_items

    def getIO(self):
        """
        Get IO instance for mouse and keyboard control.

        Returns:
            IO instance with mouse and keyboard controllers

        Example:
            client.getIO().mouse.click(100, 200)
            client.getIO().keyboard.press('space')
        """
        if self._io is None:
            from shadowlib.input.io import IO

            self._io = IO()
        return self._io

    @property
    def pathfinder(self):
        """
        Get pathfinder for navigation.

        Returns:
            Pathfinder instance

        Example:
            >>> path = client.pathfinder.getPath(3200, 3200, 0)
            >>> if path:
            ...     print(f"Path: {path.length()} tiles, {path.getTotalSeconds():.1f}s")
        """
        if self._pathfinder is None:
            from shadowlib.navigation import Pathfinder

            self._pathfinder = Pathfinder(self)
        return self._pathfinder

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
