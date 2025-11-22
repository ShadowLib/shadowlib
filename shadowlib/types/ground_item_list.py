"""
GroundItemList type with fluent filtering.
"""

from typing import Callable, List, Optional

from .ground_item import GroundItem
from .packed_position import PackedPosition


class GroundItemList:
    """
    List of ground items with fluent filtering methods.

    Supports method chaining for clean queries.
    """

    def __init__(self, items: List[GroundItem]):
        """
        Initialize ground item list.

        Args:
            items: List of GroundItem instances
        """
        self._items = items

    def filter(self, predicate: Callable[[GroundItem], bool]) -> "GroundItemList":
        """
        Filter items by custom predicate.

        Args:
            predicate: Function that takes GroundItem and returns bool

        Returns:
            Filtered GroundItemList

        Example:
            >>> items.filter(lambda item: item.quantity > 100)
        """
        return GroundItemList([item for item in self._items if predicate(item)])

    def filterById(self, item_id: int) -> "GroundItemList":
        """
        Filter by item ID.

        Args:
            item_id: Item ID to filter by

        Returns:
            Filtered GroundItemList

        Example:
            >>> coins = items.filterById(995)
        """
        return GroundItemList([item for item in self._items if item.id == item_id])

    def filterByName(self, name: str, exact: bool = False) -> "GroundItemList":
        """
        Filter by item name.

        Args:
            name: Name to search for
            exact: If True, exact match. If False, contains match (case-insensitive)

        Returns:
            Filtered GroundItemList

        Example:
            >>> coins = items.filterByName("coins")
            >>> exact_coins = items.filterByName("Coins", exact=True)
        """
        if exact:
            return GroundItemList([item for item in self._items if item.name == name])
        else:
            name_lower = name.lower()
            return GroundItemList([item for item in self._items if name_lower in item.name.lower()])

    def filterByOwnership(self, ownership: int) -> "GroundItemList":
        """
        Filter by ownership type.

        Args:
            ownership: 0 = public, 1 = yours, 2 = other player, 3 = group (yours)

        Returns:
            Filtered GroundItemList

        Example:
            >>> my_items = items.filterByOwnership(1)
            >>> public_items = items.filterByOwnership(0)
        """
        return GroundItemList([item for item in self._items if item.ownership == ownership])

    def filterYours(self) -> "GroundItemList":
        """
        Filter to only your items (ownership 1 or 3).

        Returns:
            Filtered GroundItemList

        Example:
            >>> my_items = items.filterYours()
        """
        return GroundItemList([item for item in self._items if item.isYours])

    def filterLootable(self) -> "GroundItemList":
        """
        Filter to only lootable items (yours or public).

        Returns:
            Filtered GroundItemList

        Example:
            >>> lootable = items.filterLootable()
        """
        return GroundItemList([item for item in self._items if item.canLoot])

    def filterByPosition(self, x: int, y: int, plane: int) -> "GroundItemList":
        """
        Filter to items at specific position.

        Args:
            x: X coordinate
            y: Y coordinate
            plane: Plane level

        Returns:
            Filtered GroundItemList

        Example:
            >>> items_here = items.filterByPosition(3200, 3200, 0)
        """
        target = PackedPosition(x, y, plane)
        return GroundItemList([item for item in self._items if item.position == target])

    def filterNearby(self, x: int, y: int, plane: int, radius: int) -> "GroundItemList":
        """
        Filter to items within radius of position.

        Args:
            x: Center X coordinate
            y: Center Y coordinate
            plane: Plane level
            radius: Search radius in tiles

        Returns:
            Filtered GroundItemList

        Example:
            >>> nearby = items.filterNearby(client.player.x, client.player.y, client.player.plane, 5)
        """
        center = PackedPosition(x, y, plane)
        return GroundItemList(
            [
                item
                for item in self._items
                if item.position.isNearby(center, radius, same_plane=True)
            ]
        )

    def sortByDistance(self, x: int, y: int, plane: int) -> "GroundItemList":
        """
        Sort items by distance from position (closest first).

        Args:
            x: Reference X coordinate
            y: Reference Y coordinate
            plane: Reference plane

        Returns:
            Sorted GroundItemList

        Example:
            >>> sorted_items = items.sortByDistance(client.player.x, client.player.y, client.player.plane)
        """
        center = PackedPosition(x, y, plane)
        sorted_items = sorted(self._items, key=lambda item: item.position.distanceTo(center))
        return GroundItemList(sorted_items)

    def sortByQuantity(self, reverse: bool = True) -> "GroundItemList":
        """
        Sort items by quantity.

        Args:
            reverse: If True, largest first. If False, smallest first.

        Returns:
            Sorted GroundItemList

        Example:
            >>> largest_stacks = items.sortByQuantity()
            >>> smallest_stacks = items.sortByQuantity(reverse=False)
        """
        sorted_items = sorted(self._items, key=lambda item: item.quantity, reverse=reverse)
        return GroundItemList(sorted_items)

    def first(self) -> Optional[GroundItem]:
        """
        Get first item in list.

        Returns:
            First GroundItem or None if empty

        Example:
            >>> nearest_coin = items.filterById(995).sortByDistance(...).first()
        """
        return self._items[0] if self._items else None

    def last(self) -> Optional[GroundItem]:
        """
        Get last item in list.

        Returns:
            Last GroundItem or None if empty
        """
        return self._items[-1] if self._items else None

    def isEmpty(self) -> bool:
        """Check if list is empty."""
        return len(self._items) == 0

    def count(self) -> int:
        """Get number of items in list."""
        return len(self._items)

    def toList(self) -> List[GroundItem]:
        """
        Convert to regular Python list.

        Returns:
            List of GroundItem instances
        """
        return self._items.copy()

    def __len__(self) -> int:
        """Support len() builtin."""
        return len(self._items)

    def __iter__(self):
        """Support iteration."""
        return iter(self._items)

    def __getitem__(self, index):
        """Support indexing."""
        return self._items[index]

    def __repr__(self) -> str:
        return f"GroundItemList({len(self._items)} items)"
