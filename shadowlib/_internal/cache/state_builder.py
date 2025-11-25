"""
Builds derived game state from events.

Processes raw events to maintain current state of:
- Latest-state channels (gametick, etc.)
- Ring buffer event history
- Derived state (varbits, inventory, skills, etc.)
"""

from collections import defaultdict, deque
from time import time
from typing import Any, Deque, Dict, List

import shadowlib.utilities.timing as timing
from shadowlib._internal.events.channels import LATEST_STATE_CHANNELS
from shadowlib.globals import getClient
from shadowlib.tabs.skills import SKILL_NAMES
from shadowlib.types import Item, ItemContainer


class StateBuilder:
    """
    Processes events and maintains game state.

    Converts raw event stream into actionable game state.
    Consumer calls addEvent(), users read via EventCache accessors.
    """

    def __init__(self, event_history_size: int = 100):
        """
        Initialize with empty state.

        Args:
            event_history_size: Max events to keep per ring buffer channel
        """
        # Latest-state channels (overwritten, no history)
        self.latest_states: Dict[str, Dict[str, Any]] = {}

        # Ring buffer channels (last N events)
        self.recent_events: Dict[str, Deque] = defaultdict(lambda: deque(maxlen=event_history_size))

        self.recently_changed_containers: Deque = deque(maxlen=100)

        # Derived state from ring buffer events
        self.varps: List[int] = []  # {varp_id: value}
        
        self.skills: Dict[str, Dict[str, int]] = {}  # {skill_name: {level, xp, boosted_level}}
        self.last_click: Dict[str, Any] = {}  # {button, coords, time}
        self.chat_history: Deque = deque(maxlen=100)  # Last 100 chat messages
        self.current_state: Dict[str, Any] = {}  # Other derived state as needed
        self.animating_actors: Dict[str, Any] = defaultdict(dict)  # Actors currently animating

        # Cache VarpsResource instance to avoid reloading on every varbit change
        self._varps_resource = None

        self.ground_items_initialized = False

        self.itemcontainers: Dict[int, ItemContainer] = {}

        self.itemcontainers[93] = ItemContainer(93, 28)  # Inventory
        self.itemcontainers[94] = ItemContainer(94, 14)  # Equipment
        self.itemcontainers[95] = ItemContainer(95, -1)  # Bank

    def addEvent(self, channel: str, event: Dict[str, Any]) -> None:
        """
        Process incoming event and update state.

        Called by EventConsumer thread. No lock here - EventCache handles that.

        Args:
            channel: Event channel name
            event: Event data dict
        """
        print(f"Processing event on channel {channel}: {event}")
        if channel in LATEST_STATE_CHANNELS:
            # Latest-state: just overwrite
            self.latest_states[channel] = event
        else:
            # Ring buffer: store history + update derived state
            self.recent_events[channel].append(event)
            self._processEvent(channel, event)

    def _processEvent(self, channel: str, event: Dict[str, Any]) -> None:
        """
        Update derived state from ring buffer event.

        Args:
            channel: Event channel name
            event: Event data dict
        """
        if channel == "varbit_changed":
            self._processVarbitChanged(event)
        elif channel == "item_container_changed":
            self._processItemContainerChanged(event)
        elif channel == "stat_changed":
            self._processStatChanged(event)
        elif channel == "animation_changed":
            actor_name = event.get("actor_name")
            animation_id = event.get("animation_id")
            if actor_name is not None:
                self.animating_actors[actor_name] = {
                    "animation_id": animation_id,
                    "location": event.get("location"),
                    "timestamp": event.get("_timestamp", time()),
                }
        elif channel == "chat_message":
            message = event.get("message", "")
            msgtype = event.get("type", "")
            timestamp = event.get("_timestamp", time())
            self.chat_history.append({"message": message, "type": msgtype, "timestamp": timestamp})
        elif channel == "item_spawned":
            pass  # Could implement item spawn tracking if needed
        elif channel == "item_despawned":
            pass  # Could implement item despawn tracking if needed

    def _editVarp(self, varp_id: int, new_value: int) -> None:
        """
        Set a varp to a new value.

        Args:
            varp_id: Varp index
            new_value: New 32-bit value
        """
        # Ensure varps list is large enough
        if varp_id >= len(self.varps):
            # Extend list with zeros
            self.varps.extend([0] * (varp_id - len(self.varps) + 1))

        self.varps[varp_id] = new_value

    def _editVarbit(self, varbit_id: int, varp_id: int, new_value: int) -> None:
        """
        Update a varbit value by modifying specific bits in its parent varp.

        Uses bit manipulation to preserve other bits in the varp.

        Args:
            varbit_id: Varbit index (for lookup)
            varp_id: Parent varp index
            new_value: New value for the varbit
        """
        # Get varbit metadata from resources (cached instance)
        if self._varps_resource is None:
            from shadowlib._internal.resources.varps import VarpsResource

            self._varps_resource = VarpsResource()

        varbit_info = self._varps_resource.getVarbitInfo(varbit_id)

        if not varbit_info:
            # Unknown varbit, can't determine bit positions
            # Fall back to setting the varp directly (may be incorrect)
            self._editVarp(varp_id, new_value)
            return

        # Get bit positions
        lsb = varbit_info["lsb"]  # Least significant bit
        msb = varbit_info["msb"]  # Most significant bit

        # Ensure varps list is large enough
        if varp_id >= len(self.varps):
            self.varps.extend([0] * (varp_id - len(self.varps) + 1))

        # Get current varp value
        current_varp = self.varps[varp_id]

        # Calculate bit manipulation
        num_bits = msb - lsb + 1
        bit_mask = (1 << num_bits) - 1  # Create mask for the bit range

        # Clear the bits in the current varp value
        clear_mask = ~(bit_mask << lsb)  # Invert mask and shift to position
        cleared_varp = current_varp & clear_mask

        # Insert new value at the correct position
        shifted_value = (new_value & bit_mask) << lsb
        new_varp = cleared_varp | shifted_value

        # Update the varp
        self.varps[varp_id] = new_varp

    def _processVarbitChanged(self, event: Dict[str, Any]) -> None:
        """
        Update varbit/varp state from event.

        Special case: varbit_id == -1 means update the full varp (no bit manipulation).

        Args:
            event: Varbit changed event dict with keys:
                - varbit_id: Varbit index (-1 means full varp update)
                - varp_id: Parent varp index
                - value: New value
        """
        varbit_id = event.get("varbit_id")
        varp_id = event.get("varp_id")
        value = event.get("value")

        if varp_id is None:
            return  # Invalid event

        # Special case: varbit_id == -1 means update full varp
        if varbit_id == -1 or varbit_id is None:
            self._editVarp(varp_id, value)
        else:
            # Update varbit (with bit manipulation)
            self._editVarbit(varbit_id, varp_id, value)

    def _processItemContainerChanged(self, event: Dict[str, Any]) -> None:
        """
        Update inventory/equipment/bank from event.

        Args:
            event: Item container changed event dict
        """
        container_id = event.get("container_id")
        items_list = event.get("items", [])  

        self.recently_changed_containers.append(
            [container_id, time()]
        )  # Keep track of last 100 changed containers

        if not self.itemcontainers.get(container_id):
            self.itemcontainers[container_id] = ItemContainer(container_id, -1)

        if items_list is None:
            return None
        
        self.itemcontainers[container_id].fromArray(items_list)

    def _processStatChanged(self, event: Dict[str, Any]) -> None:
        """
        Update skill levels/XP from stat_changed event.

        Event format:
        {
            'skill': 'Attack',
            'level': 75,
            'xp': 1210421,
            'boosted_level': 80  # If boosted by potion
        }

        Args:
            event: Stat changed event dict
        """
        skill_name = event.get("skill")
        if not skill_name:
            return

        # Store skill data
        self.skills[skill_name] = {
            "level": event.get("level", 1),
            "xp": event.get("xp", 0),
            "boosted_level": event.get("boosted_level", event.get("level", 1)),
        }

    def initVarps(self) -> None:
        """
        use query to get full list of varps
        """
        client = getClient()
        q = client.query()

        v = q.client.getServerVarps()
        results = q.execute({"varps": v})
        varps = results["results"].get("varps", [])
        self.varps = varps

    def initSkills(self) -> None:
        """
        use query to get full list of skills
        """
        client = getClient()
        q = client.query()

        levels = q.client.getRealSkillLevels()
        xps = q.client.getSkillExperiences()
        boosted_levels = q.client.getBoostedSkillLevels()

        results = q.execute({"levels": levels, "xps": xps, "boosted_levels": boosted_levels})
        for index, skill in enumerate(SKILL_NAMES):
            leveldata = results["results"].get("levels", {})
            xpdata = results["results"].get("xps", {})
            boosteddata = results["results"].get("boosted_levels", {})
            self.skills[skill] = {
                "level": leveldata[index],
                "xp": xpdata[index],
                "boosted_level": boosteddata[index],
            }

    def initGroundItems(self) -> None:
        """
        use query to get full list of ground items
        """
        client = getClient()

        try:
            client.api.invokeCustomMethod(
                target="EventBusListener",
                method="rebuildGroundItems",
                signature="()V",
                args=[],
                async_exec=False,
            )
        except Exception as e:
            print(f"❌ Rebuild grounditems failed: {e}")
            return


if __name__ == "__main__":
    # Simple test
    client = getClient()
    cache = client.cache
    print(time())

    timing.sleep(100)
    print(cache._state.inventory)
