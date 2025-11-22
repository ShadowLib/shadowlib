"""
Item name utilities for reverse lookup of ItemID constants.
"""

from typing import Dict, List, Optional

# Lazy import to handle missing generated files
try:
    from ..generated.constants import ItemID
except ImportError:
    ItemID = None


class ItemNames:
    """
    Utility class for reverse lookup of item names from IDs.

    Lazy-loads the reverse mapping on first use.
    """

    _id_to_name: Optional[Dict[int, str]] = None

    @classmethod
    def _buildLookup(cls) -> Dict[int, str]:
        """Build the reverse lookup dict from ItemID class."""
        if cls._id_to_name is not None:
            return cls._id_to_name

        # Check if ItemID is available
        if ItemID is None:
            raise RuntimeError(
                "ItemID constants not available. "
                "Run 'python -m src.scraper.auto_updater' to generate API data, "
                "or initialize RuneLiteAPI() to trigger auto-update."
            )

        cls._id_to_name = {}

        # Helper function to process a class's constants
        def processClass(cls_obj, prefix=""):
            for attr_name in dir(cls_obj):
                # Skip private/special attributes
                if attr_name.startswith("_"):
                    continue

                attr_value = getattr(cls_obj, attr_name)

                # Check if it's a nested class (for Noted, Placeholder)
                if isinstance(attr_value, type):
                    # Recursively process nested class
                    processClass(attr_value, prefix=attr_name + ".")
                # Only process integer constants
                elif isinstance(attr_value, int):
                    # Use prefixed name if from nested class
                    full_name = prefix + attr_name if prefix else attr_name
                    # If multiple names map to same ID, keep the first one
                    if attr_value not in cls._id_to_name:
                        cls._id_to_name[attr_value] = full_name

        # Process ItemID and its nested classes
        processClass(ItemID)

        return cls._id_to_name

    @classmethod
    def getName(cls, item_id: int) -> Optional[str]:
        """
        Get the item name for a given item ID.

        Args:
            item_id: The item ID to look up

        Returns:
            The item name (e.g., "DRAGON_SCIMITAR"), or None if not found

        Example:
            name = ItemNames.getName(4587)  # Returns "DRAGON_SCIMITAR"
        """
        lookup = cls._buildLookup()
        return lookup.get(item_id)

    @classmethod
    def getNames(cls, item_ids: List[int]) -> List[Optional[str]]:
        """
        Get item names for multiple item IDs.

        Args:
            item_ids: List of item IDs to look up

        Returns:
            List of item names (or None for IDs not found)

        Example:
            names = ItemNames.getNames([4587, 995])
            # Returns ["DRAGON_SCIMITAR", "COINS_995"]
        """
        lookup = cls._buildLookup()
        return [lookup.get(item_id) for item_id in item_ids]

    @classmethod
    def getFormattedName(cls, item_id: int) -> Optional[str]:
        """
        Get a human-readable formatted name for an item ID.

        Converts DRAGON_SCIMITAR -> "Dragon Scimitar"

        Args:
            item_id: The item ID to look up

        Returns:
            Formatted name, or None if not found

        Example:
            name = ItemNames.getFormattedName(4587)
            # Returns "Dragon Scimitar"
        """
        name = cls.getName(item_id)
        if name is None:
            return None

        # Convert DRAGON_SCIMITAR -> Dragon Scimitar
        # Split on underscore, title case each word, join with space
        words = name.split("_")
        formatted = " ".join(word.capitalize() for word in words)
        return formatted

    @classmethod
    def getFormattedNames(cls, item_ids: List[int]) -> List[Optional[str]]:
        """
        Get formatted names for multiple item IDs.

        Args:
            item_ids: List of item IDs to look up

        Returns:
            List of formatted names (or None for IDs not found)

        Example:
            names = ItemNames.getFormattedNames([4587, 995])
            # Returns ["Dragon Scimitar", "Coins 995"]
        """
        return [cls.getFormattedName(item_id) for item_id in item_ids]


# Module-level convenience functions
def getItemName(item_id: int) -> Optional[str]:
    """
    Get the item name for a given item ID.

    Args:
        item_id: The item ID to look up

    Returns:
        The item name (e.g., "DRAGON_SCIMITAR"), or None if not found

    Example:
        from shadowlib.utilities.itemNames import getItemName
        name = getItemName(4587)  # Returns "DRAGON_SCIMITAR"
    """
    return ItemNames.getName(item_id)


def getItemNames(item_ids: List[int]) -> List[Optional[str]]:
    """
    Get item names for multiple item IDs.

    Args:
        item_ids: List of item IDs to look up

    Returns:
        List of item names (or None for IDs not found)

    Example:
        from shadowlib.utilities.itemNames import getItemNames
        names = getItemNames([4587, 995])
        # Returns ["DRAGON_SCIMITAR", "COINS_995"]
    """
    return ItemNames.getNames(item_ids)


def getFormattedItemName(item_id: int) -> Optional[str]:
    """
    Get a human-readable formatted name for an item ID.

    Converts DRAGON_SCIMITAR -> "Dragon Scimitar"

    Args:
        item_id: The item ID to look up

    Returns:
        Formatted name, or None if not found

    Example:
        from shadowlib.utilities.itemNames import getFormattedItemName
        name = getFormattedItemName(4587)
        # Returns "Dragon Scimitar"
    """
    return ItemNames.getFormattedName(item_id)


def getFormattedItemNames(item_ids: List[int]) -> List[Optional[str]]:
    """
    Get formatted names for multiple item IDs.

    Args:
        item_ids: List of item IDs to look up

    Returns:
        List of formatted names (or None for IDs not found)

    Example:
        from shadowlib.utilities.itemNames import getFormattedItemNames
        names = getFormattedItemNames([4587, 995])
        # Returns ["Dragon Scimitar", "Coins 995"]
    """
    return ItemNames.getFormattedNames(item_ids)
