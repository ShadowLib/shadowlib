"""Type stubs for Client class."""

from typing import Any, Optional
from types import ModuleType

from shadowlib._internal.api import RuneLiteAPI
from shadowlib._internal.cache.event_cache import EventCache
from shadowlib.input import Input
from shadowlib.interactions import Interactions
from shadowlib.interfaces import Interfaces
from shadowlib.navigation import Navigation
from shadowlib.player import Player
from shadowlib.tabs import Tabs
from shadowlib.world import World

class _ResourcesNamespace:
    """Namespace for accessing game resources."""
    @property
    def varps(self) -> ModuleType: ...
    @property
    def objects(self) -> ModuleType: ...

class Client:
    """
    Advanced client for explicit API management.

    Most users should use the module-level functions (inventory.getItems(), etc)
    which use a global auto-connected API. Use this Client class if you need:
    - Multiple API instances
    - Explicit connection management
    - Custom API configuration
    """

    api: RuneLiteAPI
    _event_cache: EventCache

    # Namespace properties
    tabs: Tabs
    input: Input
    world: World
    navigation: Navigation
    interactions: Interactions
    interfaces: Interfaces
    player: Player
    resources: _ResourcesNamespace

    # Constants
    @property
    def ItemID(self) -> Any: ...
    @property
    def ObjectID(self) -> Any: ...
    @property
    def NpcID(self) -> Any: ...
    @property
    def AnimationID(self) -> Any: ...
    @property
    def InterfaceID(self) -> Any: ...
    @property
    def VarClientInt(self) -> Any: ...
    @property
    def VarClientStr(self) -> Any: ...

    # Cache access
    @property
    def event_cache(self) -> EventCache: ...
    @property
    def cache(self) -> EventCache: ...
    def __init__(self, api: RuneLiteAPI | None = None) -> None: ...
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def isConnected(self) -> bool: ...
    def query(self) -> Any: ...
    def __enter__(self) -> Client: ...
    def __exit__(self, *args: Any) -> None: ...
