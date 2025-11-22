"""
Channel definitions for RuneLite event system.

Ring buffer channels guarantee event delivery (files: {channel}.{seq})
Latest-state channels only keep current state (files: {channel})
"""

# Ring buffer channels - guaranteed delivery, sequential files
RING_BUFFER_CHANNELS = [
    "varbit_changed",  # Varbit/varp value changes
    "chat_message",  # Chat messages (all types)
    "item_container_changed",  # Inventory/bank/equipment changes
    "stat_changed",  # XP/level changes
    "animation_changed",  # Animation events
    "menu_entry_added",  # Menu entry additions
]

# Latest-state channels - only current state matters, file overwritten
LATEST_STATE_CHANNELS = [
    "gametick",  # Current game tick information
    "clienttick",  # Current client tick information
    "menu_option_clicked",  # Menu interaction events
    "game_state_changed",  # Game state transitions (login, loading, etc.)
    "world_view_loaded",  # World view load events
    "menu_opened",  # Menu opened events
    "ground_items",  # Current ground items state
]

# Doorbell file path - Java rings this after writing any event
DOORBELL_PATH = "/dev/shm/runelite_doorbell"

# Shared memory directory
SHM_DIR = "/dev/shm"
