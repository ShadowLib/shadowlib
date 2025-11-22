"""
OSRS ground item handling using event cache.
"""

from typing import TYPE_CHECKING

from ..types.ground_item import GroundItem
from ..types.ground_item_list import GroundItemList
from ..types.packed_position import PackedPosition

if TYPE_CHECKING:
    from ..client import Client


class GroundItems:
    """Access ground items from cache."""

    def __init__(self, client: "Client"):
        """
        Initialize ground items accessor.

        Args:
            client: The Client instance
        """
        self.client = client
        self._cached_list: GroundItemList = GroundItemList([])
        self._cached_tick: int = -1

    def getAllItems(self) -> GroundItemList:
        """
        Get all ground items from cache.

        Cached per tick (items only change once per tick).

        Returns:
            GroundItemList with all items

        Example:
            >>> # Get all items
            >>> items = client.getGroundItems().getAllItems()
            >>>
            >>> # Filter coins
            >>> coins = items.filterById(995)
            >>>
            >>> # Filter nearby items
            >>> nearby = items.filterNearby(client.player.x, client.player.y, client.player.plane, 5)
            >>>
            >>> # Chain filters
            >>> my_nearby_coins = items.filterById(995).filterYours().filterNearby(
            ...     client.player.x, client.player.y, client.player.plane, 10
            ... )
            >>>
            >>> # Get closest coin
            >>> nearest_coin = items.filterById(995).sortByDistance(
            ...     client.player.x, client.player.y, client.player.plane
            ... ).first()
        """
        current_tick = self.client.cache.tick

        # Return cached if same tick
        if self._cached_tick == current_tick and self._cached_list.count() > 0:
            return self._cached_list

        # Refresh cache
        ground_items_dict = self.client.cache.getGroundItems()
        result = []

        for packed_coord, items_list in ground_items_dict.items():
            position = PackedPosition.fromPacked(packed_coord)
            for item_data in items_list:
                result.append(GroundItem(data=item_data, position=position, client=self.client))

        self._cached_list = GroundItemList(result)
        self._cached_tick = current_tick

        return self._cached_list
