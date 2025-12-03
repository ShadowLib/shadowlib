"""
ItemContainer type for representing item containers like inventory, bank, equipment.
"""

from typing import Any, Dict, List, Optional

from shadowlib.globals import getClient
from shadowlib.types.item import Item


class ItemContainer:
    """
    Base class for OSRS item containers (inventory, bank, equipment, etc.).

    Can be used standalone as a data container or inherited by tab classes
    for additional functionality.

    Attributes:
        containerId: Unique identifier for this container
        slotCount: Number of slots in container (-1 if unknown)
        items: List of items in slots (None for empty slots)
    """

    def __init__(self, containerId: int = -1, slotCount: int = -1, items: List[Item | None] = None):
        """
        Initialize item container.

        Args:
            containerId: Unique identifier for this container (default -1)
            slotCount: Number of slots in container (-1 if unknown)
            items: List of items in slots (None for empty slots)
        """
        self.containerId = containerId
        self.slotCount = slotCount
        self.items = items if items is not None else []

    def fromArray(self, data: List[Dict[str, Any]]):
        """
        Populate ItemContainer from array of item dicts.
        Args:
            data: List of item dicts from Java response
        """
        parsedItems = [
            Item.fromDict(itemData) if itemData is not None else None for itemData in data
        ]

        self.items = parsedItems

    def populate(self):
        client = getClient()

        result = client.api.invokeCustomMethod(
            target="EventBusListener",
            method="getItemContainerPacked",
            signature="(I)[B",
            args=[self.containerId],
            async_exec=False,
        )

        if result:
            self.fromArray(result)

    def toDict(self) -> Dict[str, Any]:
        """
        Convert ItemContainer back to dict format.

        Returns:
            Dict with 'containerId', 'slotCount', 'items'
        """
        return {
            "containerId": self.containerId,
            "slotCount": self.slotCount,
            "items": [item.toDict() if item is not None else None for item in self.items],
        }

    def getTotalCount(self) -> int:
        """
        Get count of non-empty slots.

        Returns:
            Number of items (non-None slots)
        """
        return sum(1 for item in self.items if item is not None)

    def getTotalQuantity(self) -> int:
        """
        Get total quantity of all items (sum of stacks).

        Returns:
            Total item quantity across all slots
        """
        return sum(item.quantity for item in self.items if item is not None)

    def getItemCount(self, id: int) -> int:
        """
        Get count of items matching the given ID.

        Args:
            id: Item ID to count

        Returns:
            Number of items with matching ID
        """
        return sum(1 for item in self.items if item is not None and item.id == id)

    def getItemCountByName(self, name: str) -> int:
        """
        Get count of items matching the given name.

        Args:
            name: Item name to count

        Returns:
            Number of items with matching name
        """
        return sum(1 for item in self.items if item is not None and item.name in name)

    def getItemsById(self, itemId: int) -> List[Item]:
        """
        Get all items matching the given ID.

        Args:
            itemId: Item ID to search for

        Returns:
            List of all Items with matching ID
        """
        return [item for item in self.items if item is not None and item.id == itemId]

    def getItemsByName(self, name: str) -> List[Item]:
        """
        Get all items matching the given name.

        Args:
            name: Item name to search for

        Returns:
            List of all Items with matching name
        """
        return [item for item in self.items if item is not None and item.name in name]

    def getSlot(self, slotIndex: int) -> Item | None:
        """
        Get item at specific slot index.

        Args:
            slotIndex: Slot index (0-based)

        Returns:
            Item at slot, or None if empty or out of range
        """
        if 0 <= slotIndex < len(self.items):
            return self.items[slotIndex]
        return None

    def getSlots(self, slots: List[int]) -> List[Item | None]:
        """
        Get items at specific slot indices.

        Args:
            slots: List of slot indices (0-based)

        Returns:
            List of Items or None for each requested slot
        """
        result = []
        for slotIndex in slots:
            if 0 <= slotIndex < len(self.items):
                result.append(self.items[slotIndex])
            else:
                result.append(None)
        return result

    def findItemSlot(self, id: int) -> int | None:
        """
        Find the first slot index containing an item with the given ID.

        Args:
            id: Item ID to search for

        Returns:
            Slot index if found, else None
        """
        for index, item in enumerate(self.items):
            if item is not None and item.id == id:
                return index
        return None

    def findItemSlots(self, id: int) -> List[int]:
        """
        Find all slot indices containing items with the given ID.

        Args:
            id: Item ID to search for

        Returns:
            List of slot indices
        """
        slots = []
        for index, item in enumerate(self.items):
            if item is not None and item.id == id:
                slots.append(index)
        return slots

    def findItemSlotsByName(self, name: str) -> List[int]:
        """
        Find all slot indices containing items with the given name.

        Args:
            name: Item name to search for

        Returns:
            List of slot indices
        """
        slots = []
        for index, item in enumerate(self.items):
            if item is not None and item.name in name:
                slots.append(index)
        return slots

    def containsItem(self, id: int) -> bool:
        """
        Check if container contains an item with the given ID.

        Args:
            id: Item ID to check

        Returns:
            True if item with ID exists in container
        """
        return any(item is not None and item.id == id for item in self.items)

    def containsItemByName(self, name: str) -> bool:
        """
        Check if container contains an item with the given name.

        Args:
            name: Item name to check

        Returns:
            True if item with name exists in container
        """
        return any(item is not None and item.name in name for item in self.items)

    def containsAllItems(self, ids: List[int]) -> bool:
        """
        Check if container contains all items with the given IDs.

        Args:
            ids: List of item IDs to check

        Returns:
            True if all item IDs exist in container
        """
        return all(any(item is not None and item.id == id for item in self.items) for id in ids)

    def containsAllItemsByName(self, names: List[str]) -> bool:
        """
        Check if container contains all items with the given names.

        Args:
            names: List of item names to check

        Returns:
            True if all item names exist in container
        """
        return all(
            any(item is not None and item.name in name for item in self.items) for name in names
        )

    def isEmpty(self) -> bool:
        """
        Check if container has no items.

        Returns:
            True if all slots are None
        """
        return all(item is None for item in self.items)

    def isFull(self) -> bool:
        """
        Check if container is full.

        Returns:
            True if no empty slots remain (considers slotCount if known)
        """
        if self.slotCount > 0:
            return self.getTotalCount() >= self.slotCount
        return all(item is not None for item in self.items)

    def __repr__(self) -> str:
        """String representation."""
        return f"ItemContainer(id={self.containerId}, items={self.toDict()})"

    def __eq__(self, other) -> bool:
        """Check equality with another ItemContainer."""
        if not isinstance(other, ItemContainer):
            return False
        return (
            self.containerId == other.containerId
            and self.slotCount == other.slotCount
            and self.items == other.items
        )
