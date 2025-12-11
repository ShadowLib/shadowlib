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

import numpy as np

import shadowlib.utilities.timing as timing
from shadowlib._internal.events.channels import LATEST_STATE_CHANNELS
from shadowlib._internal.resources import varps as varps_resource
from shadowlib.globals import getApi
from shadowlib.types import Item, ItemContainer

# Skill names constant - defined here to avoid circular import with tabs.skills singleton
# Note: Also defined in tabs/skills.py for public API access
SKILL_NAMES = [
    "Attack",
    "Defence",
    "Strength",
    "Hitpoints",
    "Ranged",
    "Prayer",
    "Magic",
    "Cooking",
    "Woodcutting",
    "Fletching",
    "Fishing",
    "Firemaking",
    "Crafting",
    "Smithing",
    "Mining",
    "Herblore",
    "Agility",
    "Thieving",
    "Slayer",
    "Farming",
    "Runecrafting",
    "Hunter",
    "Construction",
    "Sailing",
]


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
        self.varcs: Dict[int, Any] = {}  # {varc_id: value}

        self.skills: Dict[str, Dict[str, int]] = {}  # {skill_name: {level, xp, boosted_level}}
        self.last_click: Dict[str, Any] = {}  # {button, coords, time}
        self.chat_history: Deque = deque(maxlen=100)  # Last 100 chat messages
        self.current_state: Dict[str, Any] = {}  # Other derived state as needed
        self.animating_actors: Dict[str, Any] = defaultdict(dict)  # Actors currently animating

        self.ground_items_initialized = False
        self.varps_initialized = False
        self.varcs_initialized = False
        self.skills_initialized = False
        self.containers_initialized = False

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
        if channel in ["scene_objects"]:
            print(f"got event {channel} ")  # --- IGNORE ---

        if channel in LATEST_STATE_CHANNELS:
            # Latest-state: just overwrite
            event["_timestamp"] = time()
            self.latest_states[channel] = event

            # Handle projection-related events immediately
            if channel == "world_view_loaded":
                self._processWorldViewLoaded(event)
            elif channel in ("camera_changed", "world_entity"):
                self._processCameraChanged()
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
        elif channel in ["var_client_int_changed", "var_client_str_changed"]:
            self._processVarcChanged(event)
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

    def _editVarc(self, varc_id: int, new_value: Any) -> None:
        """
        Set a varc to a new value.

        Args:
            varc_id: Varc index
            new_value: New value (any type)
        """
        if (len(self.varcs) == 0) and (not self.varcs_initialized):
            self.initVarcs()
        self.varcs[varc_id] = new_value

    def _editVarbit(self, varbit_id: int, varp_id: int, new_value: int) -> None:
        """
        Update a varbit value by modifying specific bits in its parent varp.

        Uses bit manipulation to preserve other bits in the varp.

        Args:
            varbit_id: Varbit index (for lookup)
            varp_id: Parent varp index
            new_value: New value for the varbit
        """
        # Get varbit metadata from resources (direct import to avoid race condition)
        varbit_info = varps_resource.getVarbitInfo(varbit_id)

        if not varbit_info:
            return

        # Get bit positions
        lsb = varbit_info["lsb"]  # Least significant bit
        msb = varbit_info["msb"]  # Most significant bit

        # Ensure varps list is large enough
        if varp_id >= len(self.varps) and not self.varps_initialized:
            self.initVarps()
            if varp_id >= len(self.varps):
                return  # Invalid varp_id

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

    def _processVarcChanged(self, event: Dict[str, Any]) -> None:
        """
        Update varc state from event.

        Args:
            event: Varc changed event dict with keys:
                - varc_id: Varc index
                - value: New value
        """
        varc_id = event.get("varc_id")
        value = event.get("value")

        if varc_id is None:
            return  # Invalid event

        self._editVarc(varc_id, value)

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
        api = getApi()
        q = api.query()

        v = q.client.getServerVarps()
        results = q.execute({"varps": v})
        varps = results["results"].get("varps", [])
        if len(varps) > 1000:
            self.varps = varps
            self.varps_initialized = True

    def initVarcs(self) -> None:
        """
        use query to get full list of varcs
        """
        api = getApi()
        q = api.query()

        v = q.client.getVarcMap()
        results = q.execute({"varcs": v})
        varcs = results["results"].get("varcs", {})
        if len(varcs) > 0:
            self.varcs = varcs
            self.varcs_initialized = True

    def initSkills(self) -> None:
        """
        use query to get full list of skills
        """
        api = getApi()
        q = api.query()

        levels = q.client.getRealSkillLevels()
        xps = q.client.getSkillExperiences()
        boosted_levels = q.client.getBoostedSkillLevels()

        results = q.execute({"levels": levels, "xps": xps, "boosted_levels": boosted_levels})
        if len(results["results"].get("levels", {})) > 0:
            self.skills_initialized = True
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
        api = getApi()

        try:
            api.invokeCustomMethod(
                target="EventBusListener",
                method="rebuildGroundItems",
                signature="()V",
                args=[],
                async_exec=False,
            )
        except Exception as e:
            print(f"❌ Rebuild grounditems failed: {e}")
            return

    def _processCameraChanged(self) -> None:
        """Invalidate tile projection cache when camera changes."""
        from shadowlib.world.projection import projection

        projection.invalidate()

    def _processWorldViewLoaded(self, event: Dict[str, Any]) -> None:
        """
        Configure Projection singleton when world_view_loaded event is received.

        This is called immediately when the event arrives, ensuring the projection
        module always has correct scene data.

        Args:
            event: World view loaded event with keys:
                - tile_heights: Flat list of heights [4 * sizeX * sizeY]
                - bridge_flags: Flat list of bools (may be smaller than sizeX * sizeY)
                - base_x, base_y: Scene base coordinates
                - size_x, size_y: Scene dimensions
                - boundsX, boundsY, boundsWidth, boundsHeight: Entity bounds (0 for top-level)
                - plane: Current plane
        """
        from shadowlib.world.projection import EntityConfig, projection

        # Extract scene data
        sizeX = event.get("size_x", 104)
        sizeY = event.get("size_y", 104)

        # Convert flat tile_heights list to [4, sizeX, sizeY] array
        tileHeightsList = event.get("tile_heights", [])
        if tileHeightsList:
            expectedTileSize = 4 * sizeX * sizeY
            if len(tileHeightsList) == expectedTileSize:
                tileHeights = np.array(tileHeightsList, dtype=np.int32).reshape(4, sizeX, sizeY)
            else:
                # Handle size mismatch - pad or truncate
                arr = np.zeros(expectedTileSize, dtype=np.int32)
                arr[: min(len(tileHeightsList), expectedTileSize)] = tileHeightsList[
                    :expectedTileSize
                ]
                tileHeights = arr.reshape(4, sizeX, sizeY)
        else:
            # Fallback to zeros if no data
            tileHeights = np.zeros((4, sizeX, sizeY), dtype=np.int32)

        # Convert flat bridge_flags list to [sizeX, sizeY] array
        # Note: bridge_flags may be (sizeX-1)*(sizeY-1) or other sizes
        bridgeFlagsList = event.get("bridge_flags", [])
        bridgeFlags = np.zeros((sizeX, sizeY), dtype=np.bool_)
        if bridgeFlagsList:
            flagLen = len(bridgeFlagsList)
            # Try to infer the correct dimensions
            if flagLen == sizeX * sizeY:
                bridgeFlags = np.array(bridgeFlagsList, dtype=np.bool_).reshape(sizeX, sizeY)
            elif flagLen == (sizeX - 1) * (sizeY - 1):
                # Bridge flags may be for interior tiles only
                inner = np.array(bridgeFlagsList, dtype=np.bool_).reshape(sizeX - 1, sizeY - 1)
                bridgeFlags[:-1, :-1] = inner
            else:
                # Best effort: reshape to square if possible, otherwise fill what we can
                side = int(np.sqrt(flagLen))
                if side * side == flagLen and side <= sizeX and side <= sizeY:
                    inner = np.array(bridgeFlagsList, dtype=np.bool_).reshape(side, side)
                    bridgeFlags[:side, :side] = inner

        baseX = event.get("base_x", 0)
        baseY = event.get("base_y", 0)

        # Set scene data on projection singleton and invalidate cache
        projection.setScene(tileHeights, bridgeFlags, baseX, baseY, sizeX, sizeY)
        projection.invalidate()

        # Handle entity config (for WorldEntity instances)
        # When on top-level, bounds are all 0, which means identity transform
        boundsX = event.get("boundsX", 0)
        boundsY = event.get("boundsY", 0)
        boundsWidth = event.get("boundsWidth", 0)
        boundsHeight = event.get("boundsHeight", 0)

        # Only set entity config if we have non-zero bounds (inside a WorldEntity)
        if boundsWidth > 0 or boundsHeight > 0:
            config = EntityConfig(
                boundsX=boundsX, boundsY=boundsY, boundsWidth=boundsWidth, boundsHeight=boundsHeight
            )
            projection.setEntityConfig(config)
        else:
            # Top-level world: use None for identity transform
            projection.setEntityConfig(None)
