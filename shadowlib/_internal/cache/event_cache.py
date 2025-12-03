"""
Thread-safe public API for accessing game state.

Wraps StateBuilder with thread safety and provides clean public methods.
"""

import threading
import time
from typing import Any, Dict, List

from shadowlib.types import ItemContainer
from shadowlib.utilities.timing import waitUntil

from .state_builder import StateBuilder


class EventCache:
    """
    Thread-safe public API for game state.

    Wraps StateBuilder (which processes events) and adds:
    - Thread safety via RLock
    - Clean public methods
    - Convenience properties

    Consumer → StateBuilder.addEvent() → Updates state
    User → EventCache methods → Read state (with lock)
    """

    def __init__(self, event_history_size: int = 100):
        """
        Initialize event cache.

        Args:
            event_history_size: Maximum events to keep per ring buffer channel
        """
        # StateBuilder does the actual work
        self._state = StateBuilder(event_history_size)

        # Track last update time
        self._last_update_time: float = 0.0

        # Thread safety - protects all access to _state
        self._lock = threading.RLock()

    def addEvent(self, channel: str, event: Dict[str, Any]) -> None:
        """
        Add event from EventConsumer.

        Thread-safe wrapper that calls StateBuilder.addEvent() with lock protection.

        Args:
            channel: Event channel name
            event: Event data dict
        """
        with self._lock:
            self._state.addEvent(channel, event)
            self._last_update_time = time.time()

    def getGametickState(self) -> Dict[str, Any]:
        """
        Get latest gametick state.

        Returns copy of gametick data from StateBuilder.latest_states.

        Returns:
            Dict with tick, energy, position, etc.
        """
        with self._lock:
            return self._state.latest_states.get("gametick", {}).copy()

    def getRecentEvents(self, channel: str, n: int | None = None) -> List[Dict[str, Any]]:
        """
        Get recent events from ring buffer channel.

        Reads from StateBuilder.recent_events deque.

        Args:
            channel: Channel name (e.g., 'chat_message', 'stat_changed')
            n: Number of events to return (None = all, up to 100)

        Returns:
            List of event dicts (newest last)
        """
        with self._lock:
            events = list(self._state.recent_events[channel])
            if n is not None:
                events = events[-n:]
            return events

    def getAllRecentEvents(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all recent events across all ring buffer channels.

        Reads all deques from StateBuilder.recent_events.

        Returns:
            Dict mapping channel name to list of events
        """
        with self._lock:
            return {channel: list(events) for channel, events in self._state.recent_events.items()}

    def getLastUpdateTime(self) -> float:
        """
        Get timestamp of last cache update.

        Returns:
            Unix timestamp (seconds since epoch)
        """
        with self._lock:
            return self._last_update_time

    def getAge(self) -> float:
        """
        Get age of cached data in seconds.

        Returns:
            Seconds since last update
        """
        with self._lock:
            if self._last_update_time == 0:
                return float("inf")
            return time.time() - self._last_update_time

    def isFresh(self, max_age: float = 1.0) -> bool:
        """
        Check if cache data is fresh.

        Args:
            max_age: Maximum acceptable age in seconds

        Returns:
            True if data age < max_age
        """
        return self.getAge() < max_age

    def clear(self) -> None:
        """
        Clear all cached data.

        Clears StateBuilder state and resets update time.
        """
        with self._lock:
            self._state.latest_states.clear()
            self._state.recent_events.clear()
            self._state.varbits.clear()
            self._state.skills.clear()
            self._state.inventory = [-1] * 28
            self._state.equipment.clear()
            self._state.bank.clear()
            self._last_update_time = 0.0

    # Convenience properties for common gametick state fields
    @property
    def tick(self) -> int | None:
        """Get current game tick from latest gametick state."""
        gametick = self._state.latest_states.get("gametick", {})
        return gametick.get("tick")

    @property
    def energy(self) -> int | None:
        """Get current run energy (0-10000) from latest gametick state."""
        gametick = self._state.latest_states.get("gametick", {})
        return gametick.get("energy")

    @property
    def position(self) -> Dict[str, int] | None:
        """Get current player position {x, y, plane} from latest gametick state."""
        gametick = self._state.latest_states.get("gametick", {})
        return gametick.get("position")

    def getVarp(self, varp_id: int) -> int | None:
        """
        Get current value of a varp from cache.

        Looks up in StateBuilder.varps list (built from varbit_changed events).

        Args:
            varp_id: Varp ID to query

        Returns:
            Current value or None if not set
        """
        with self._lock:
            if len(self._state.varps) < varp_id + 1 and not self._state.varps_initialized:
                self._state.initVarps()
            if varp_id >= len(self._state.varps):
                return None
            return self._state.varps[varp_id]
    
    def getVarc(self, varc_id: int) -> Any | None:
        """
        Get current value of a varc from cache.

        Looks up in StateBuilder.varcs dict (built from var_client_int_changed and var_client_str_changed events).

        Args:
            varc_id: Varc ID to query
        Returns:
            Current value or None if not set
        """
        with self._lock:
            varc = self._state.varcs.get(varc_id, None)
            if varc is None and not self._state.varcs_initialized:
                self._state.initVarcs()
                varc = self._state.varcs.get(varc_id, None)
            return varc

    def getAllSkills(self) -> Dict[str, Dict[str, int]]:
        """
        Get all tracked skills.

        Returns copy of StateBuilder.skills dict.

        Returns:
            Dict mapping skill name to skill data

        Example:
            skills = cache.getAllSkills()
            for name, data in skills.items():
                print(f"{name}: Level {data['level']} (XP: {data['xp']})")
        """
        with self._lock:
            if not len(self._state.skills) == 24:
                self._state.initSkills()
            return self._state.skills.copy()

    def getGroundItems(self) -> Dict[int, Any]:
        """
        Get current ground items state.

        Returns copy of StateBuilder.latest_states['ground_items'].
        item format is e.g. {100665727: [{'quantity': 1, 'ownership': 0, 'name': 'Tinderbox', 'id': 590}], ...} where the keys are packed coordinates.

        Returns:
            List of ground item dicts
        """
        with self._lock:
            if (
                self._state.latest_states.get("ground_items") is None
                and not self._state.ground_items_initialized
            ):
                self._state.initGroundItems()
                if waitUntil(self._state.latest_states.get("ground_items") is not None, timeout=5):
                    self._state.ground_items_initialized = True

            return self._state.latest_states.get("ground_items", {}).copy()

    def getItemContainer(self, container_id: int) -> ItemContainer | None:
        """
        Get current item container state by ID.

        Args:
            container_id: Container ID (93=inventory, 94=equipment, 95=bank)

        Returns:
            ItemContainer object or None if not found
        """
        with self._lock:
            containers = self._state.itemcontainers
            if not containers:
                return None

            if container_id in [93, 94] and not self._state.containers_initialized:
                self._state.itemcontainers.get(93, None).populate()
                self._state.itemcontainers.get(94, None).populate()
                self._state.containers_initialized = True

            if container_id not in containers:
                containers[container_id] = ItemContainer(container_id, -1)

            return self._state.itemcontainers.get(container_id, None)
        
    def getMenuState(self) -> Dict[str, Any]:
        """
        Get latest menu state.

        Returns copy of menu data from StateBuilder.latest_states.

        Returns:
            Dict with _timestampt, menuX, menuY, width and height
        """
        with self._lock:
            return self._state.latest_states.get("menu_opened", {}).copy()
        
    def getMenuOptions(self) -> List[Dict[str, Any]]:
        """
        Get latest menu options.

        Returns copy of menu options from StateBuilder.latest_states.

        Returns:
            List of menu option dicts
        """
        with self._lock:
            menu_state = self._state.latest_states.get("post_menu_sort", {}).copy()
            return menu_state
        
    def getClientTickState(self) -> Dict[str, Any]:
        """
        Get latest client tick state.

        Returns copy of client tick data from StateBuilder.latest_states.

        Returns:
            Dict with client tick information
        """
        with self._lock:
            return self._state.latest_states.get("clienttick", {}).copy()
        
    def getMenuClickedState(self) -> Dict[str, Any]:
        """
        Get latest menu option clicked state.

        Returns copy of menu option clicked data from StateBuilder.latest_states.

        Returns:
            Dict with menu option clicked information
        """
        with self._lock:
            return self._state.latest_states.get("menu_option_clicked", {}).copy()


if __name__ == "__main__":
    # Simple test
    cache = EventCache()
    print(cache.getSkill("Attack"))
