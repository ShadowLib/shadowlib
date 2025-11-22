"""
Ground item type definition.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from .packed_position import PackedPosition

if TYPE_CHECKING:
    from ..client import Client


@dataclass
class GroundItem:
    """
    Represents a ground item from cache.

    Attributes:
        data: Raw item data dict from cache
        position: PackedPosition of the item
        client: Client instance
    """

    data: Dict[str, Any]
    position: PackedPosition
    client: "Client"

    @property
    def id(self) -> int:
        """Get item ID."""
        return self.data.get("id", -1)

    @property
    def name(self) -> str:
        """Get item name."""
        return self.data.get("name", "Unknown")

    @property
    def quantity(self) -> int:
        """Get item quantity."""
        return self.data.get("quantity", 1)

    @property
    def ownership(self) -> int:
        """
        Get ownership state.

        Returns:
            0 = public, 1 = yours, 2 = other player, 3 = group (also yours)
        """
        return self.data.get("ownership", 0)

    @property
    def x(self) -> int:
        """Get X coordinate."""
        return self.position.x

    @property
    def y(self) -> int:
        """Get Y coordinate."""
        return self.position.y

    @property
    def plane(self) -> int:
        """Get plane level."""
        return self.position.plane

    @property
    def coord(self) -> tuple:
        """Get (x, y, plane) tuple."""
        return self.position.unpack()

    @property
    def isYours(self) -> bool:
        """Check if this item belongs to you."""
        return self.ownership in (1, 3)

    @property
    def canLoot(self) -> bool:
        """Check if you can loot this item (yours or public)."""
        return self.ownership in (0, 1, 3)

    @property
    def isPublic(self) -> bool:
        """Check if this item is visible to everyone."""
        return self.ownership == 0

    def distanceFromPlayer(self) -> int:
        """
        Calculate distance from player to this item.

        Returns:
            Distance in tiles (Chebyshev distance)
        """
        player_pos = PackedPosition(
            self.client.player.x, self.client.player.y, self.client.player.plane
        )
        return self.position.distanceTo(player_pos)

    def __repr__(self) -> str:
        ownership_str = {0: "public", 1: "yours", 2: "other", 3: "yours_tradeable"}.get(
            self.ownership, "unknown"
        )
        return (
            f"GroundItem(id={self.id}, name='{self.name}', "
            f"quantity={self.quantity}, position={self.position}, "
            f"ownership={ownership_str})"
        )
