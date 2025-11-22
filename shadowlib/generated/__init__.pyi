"""Type stubs for generated modules"""
# This helps IDEs find the generated types even before they're generated

from typing import TYPE_CHECKING

# Re-export query_proxies types for autocomplete
if TYPE_CHECKING:
    from .query_proxies import (
        ClientProxy,
        GameObjectProxy,
        InventoryProxy,
        # Add more as needed
        NPCProxy,
        PlayerProxy,
    )

__all__ = [
    "ClientProxy",
    "PlayerProxy",
    "NPCProxy",
    "GameObjectProxy",
    "InventoryProxy",
]
