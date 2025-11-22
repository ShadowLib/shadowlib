"""
Item type for representing game items.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Item:
    """
    Represents an OSRS item.

    Attributes:
        id: Item ID
        name: Item name
        quantity: Stack size (how many of this item)
        noted: Whether the item is noted
    """

    id: int
    name: str
    quantity: int
    noted: bool

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "Item":
        """
        Convert dict from Java to Item instance.

        Java sends:
            info.put("id", itemId);
            info.put("name", comp.getName());
            info.put("stack", qty);
            info.put("noted", comp.getNote() != -1);

        Args:
            data: Dict with 'id', 'name', 'stack', 'noted'

        Returns:
            Item instance

        Example:
            data = {'id': 995, 'name': 'Coins', 'stack': 1000, 'noted': False}
            item = Item.fromDict(data)
            print(item.name)  # "Coins"
            print(item.quantity)  # 1000
        """
        return cls(
            id=data.get("id", -1),
            name=data.get("name", "Unknown"),
            quantity=data.get("stack", 1),
            noted=data.get("noted", False),
        )

    def toDict(self) -> Dict[str, Any]:
        """
        Convert Item back to dict format.

        Returns:
            Dict with 'id', 'name', 'stack', 'noted'
        """
        return {"id": self.id, "name": self.name, "stack": self.quantity, "noted": self.noted}

    def __repr__(self) -> str:
        """String representation."""
        noted_str = " (noted)" if self.noted else ""
        return f"Item({self.id}, '{self.name}' x{self.quantity}{noted_str})"
