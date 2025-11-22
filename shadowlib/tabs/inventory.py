"""
Inventory tab module.
"""

from typing import Any, Dict, List, Optional

from shadowlib.utilities.geometry import createGrid
from shadowlib.utilities.itemNames import getFormattedItemName, getItemName

from .gametab import GameTab, GameTabs


class Inventory(GameTabs):
    """
    Inventory operations class.
    Can be used directly or via module-level functions.
    """

    TAB_TYPE = GameTab.INVENTORY  # This tab represents the inventory
    INVENTORY_ID = 93  # RuneLite inventory container ID

    def __init__(self, client=None):
        """
        Initialize inventory manager.

        Args:
            client: Optional Client instance. If None, uses global Client.
        """
        super().__init__(client)

        # Create inventory slot grid (4 columns x 7 rows, 28 slots total)
        # Slot 0 starts at (563, 213), each slot is 36x32 pixels with 6px horizontal spacing
        # 2px padding on all sides to avoid misclicks on edges
        self.slots = createGrid(
            start_x=563,
            start_y=213,
            width=36,
            height=32,
            columns=4,
            rows=7,
            spacing_x=6,
            spacing_y=4,  # Vertical spacing between rows
            padding=1,  # 2px padding on all sides to avoid edge misclicks
        )

    def getItemIds(self) -> List[int]:
        """
        Get all items in the inventory.

        Returns:
            List of item IDs in inventory slots (length 28).
        """
        # Ensure cache is initialized
        items = self.client.cache["inventory"]

        if len(items) < 28:
            # Adding -1 for empty slots if fewer than 28 items
            items += [-1] * (28 - len(items))

        return items

    def getItemQuantities(self) -> List[int]:
        """
        Get all item quantities in the inventory.

        Returns:
            List of item quantities in inventory slots (length 28).
        """
        # Ensure cache is initialized
        quantities = self.client.cache["inventory_quantities"]

        if len(quantities) < 28:
            # Adding 0 for empty slots if fewer than 28 items
            quantities += [0] * (28 - len(quantities))

        return quantities

    def slotsUsed(self) -> int:
        """
        Get number of used inventory slots.

        Returns:
            Number of non-empty inventory slots (0-28).
        """
        items = self.getItemIds()
        return sum(1 for item in items if item != -1)

    def totalQuantity(self) -> int:
        """
        Get total quantity of all items in inventory.

        Returns:
            Sum of quantities of all items in inventory.
        """
        quantities = self.getItemQuantities()
        return sum(quantities)

    def isFull(self) -> bool:
        return self.slotsUsed() >= 28

    def getItemsWithNames(self, formatted: bool = False) -> List[Dict[str, Any]]:
        """
        Get all items in inventory with their names and quantities.

        Args:
            formatted: If True, uses human-readable names (e.g., "Dragon Scimitar").
                      If False, uses raw names (e.g., "DRAGON_SCIMITAR").

        Returns:
            List of dictionaries containing item info for each slot:
            [
                {
                    'slot': 0,
                    'id': 4587,
                    'name': 'Dragon Scimitar' or 'DRAGON_SCIMITAR',
                    'quantity': 1
                },
                ...
            ]
            Empty slots have id=-1 and name=None.

        Example:
            # Get all items with formatted names
            items = inventory.getItemsWithNames(formatted=True)
            for item in items:
                if item['id'] != -1:
                    print(f"Slot {item['slot']}: {item['name']} x{item['quantity']}")

            # Get all items with raw names
            items = inventory.getItemsWithNames()
            for item in items:
                if item['name'] == 'DRAGON_SCIMITAR':
                    print(f"Found Dragon Scimitar in slot {item['slot']}")
        """
        ids = self.getItemIds()
        quantities = self.getItemQuantities()

        result = []
        name_func = getFormattedItemName if formatted else getItemName

        for slot, (item_id, quantity) in enumerate(zip(ids, quantities)):
            result.append(
                {
                    "slot": slot,
                    "id": item_id,
                    "name": name_func(item_id) if item_id != -1 else None,
                    "quantity": quantity,
                }
            )

        return result

    def getNonEmptyItemsWithNames(self, formatted: bool = False) -> List[Dict[str, Any]]:
        """
        Get only non-empty inventory slots with their names and quantities.

        Args:
            formatted: If True, uses human-readable names (e.g., "Dragon Scimitar").
                      If False, uses raw names (e.g., "DRAGON_SCIMITAR").

        Returns:
            List of dictionaries containing item info (empty slots excluded):
            [
                {
                    'slot': 0,
                    'id': 4587,
                    'name': 'Dragon Scimitar' or 'DRAGON_SCIMITAR',
                    'quantity': 1
                },
                ...
            ]

        Example:
            # Get only items that exist (no empty slots)
            items = inventory.getNonEmptyItemsWithNames(formatted=True)
            print(f"You have {len(items)} items:")
            for item in items:
                print(f"  {item['name']} x{item['quantity']}")
        """
        all_items = self.getItemsWithNames(formatted=formatted)
        return [item for item in all_items if item["id"] != -1]

    def containsItem(self, item_id: int) -> bool:
        """
        Check if inventory contains at least one of an item.

        Args:
            item_id: The item ID to check for
        Returns:
            True if item exists in inventory, False otherwise

        Example:
            if inventory.contains(1511):
                print("You have logs!")
        """
        items = self.getItemIds()
        if item_id in items:
            return True
        return False

    def findItemSlots(self, item_id: int) -> List[int]:
        """
        Find all inventory slots containing a specific item.

        Args:
            item_id: The item ID to search for

        Returns:
            List of slot indices (0-27) where the item is found.
            Empty list if item not found.

        Example:
            slots = inventory.findItemSlots(1511)  # Normal logs
            print(f"Logs found in slots: {slots}")
        """
        items = self.getItemIds()
        return [index for index, id in enumerate(items) if id == item_id]

    def getItemCount(self, item_id: int) -> int:
        """
        Count how many of a specific item are in inventory.

        Args:
            item_id: The item ID to count

        Returns:
            Number of items with that ID

        Example:
            logs_count = inventory.getItemCount(1511)  # Normal logs
            print(f"You have {logs_count} logs")
        """
        slots = self.findItemSlots(item_id)
        if not slots:
            return 0

        items, counts = self.getItemIds(), self.getItemQuantities()
        # filter slots to only those containing the item
        filtereditems, filteredcounts = (
            [item for index, item in enumerate(items) if index in slots],
            [count for index, count in enumerate(counts) if index in slots],
        )

        if len(filtereditems) > 1:
            return len(filtereditems)
        return filteredcounts[0]

    def contains(self, item_id: int) -> bool:
        """
        Check if inventory contains at least one of an item.

        Args:
            item_id: The item ID to check for

        Returns:
            True if item exists in inventory, False otherwise

        Example:
            if inventory.contains(1511):
                print("You have logs!")
        """
        return self.getItemCount(item_id) > 0

    def isFull(self) -> bool:
        """
        Check if inventory is full (28 items).

        Returns:
            True if inventory has 28 items, False otherwise

        Example:
            if inventory.isFull():
                print("Inventory is full, time to bank!")
        """
        items = self.getItemIds()
        # Count non-empty slots (item ID != -1)
        return sum(1 for item in items if item != -1) >= 28

    def isEmpty(self) -> bool:
        """
        Check if inventory is empty.

        Returns:
            True if inventory has no items, False otherwise

        Example:
            if inventory.isEmpty():
                print("Inventory is empty, ready to start!")
        """
        items = self.getItemIds()
        return all(item == -1 for item in items)

    def countEmptySlots(self) -> int:
        """
        Get number of free inventory slots.

        Returns:
            Number of empty slots (0-28)

        Example:
            free = inventory.get_free_slots()
            print(f"You have {free} free slots")
        """
        items = self.getItemIds()
        return sum(1 for item in items if item == -1)

    def hoverItem(
        self, item_id: int, slot_index: Optional[int] = None, duration: float = 0.2
    ) -> bool:
        """
        Hover over an item in the inventory.

        Args:
            item_id: The item ID to hover over
            slot_index: Specific slot index (0-27) to hover. If None, hovers first found slot.
            duration: Time to take moving to the item (seconds)

        Returns:
            True if item was found and hovered, False otherwise

        Example:
            # Hover over first logs found
            inventory.hoverItem(1511)

            # Hover over logs in slot 5
            inventory.hoverItem(1511, slot_index=5)
        """
        if slot_index is not None:
            # Hover specific slot
            if 0 <= slot_index < 28:
                items = self.getItemIds()
                if items[slot_index] == item_id:
                    self.slots[slot_index].hover(duration=duration)
                    return True
            return False

        # Find first slot with the item
        slots = self.findItemSlots(item_id)
        if not slots:
            return False

        # Hover the first slot
        self.slots[slots[0]].hover(duration=duration)
        return True

    def hoverSlot(self, slot_index: int, duration: float = 0.2) -> bool:
        """
        Hover over a specific inventory slot regardless of contents.

        Args:
            slot_index: Slot index (0-27) to hover
            duration: Time to take moving to the slot (seconds)

        Returns:
            True if slot index is valid, False otherwise

        Example:
            # Hover over slot 0 (top-left)
            inventory.hoverSlot(0)

            # Hover over slot 27 (bottom-right)
            inventory.hoverSlot(27)
        """
        if 0 <= slot_index < 28:
            self.slots[slot_index].hover(duration=duration)
            return True
        return False

    def clickItem(
        self,
        item_id: int,
        slot_index: Optional[int] = None,
        button: str = "left",
        duration: float = 0.2,
    ) -> bool:
        """
        Click an item in the inventory.

        Args:
            item_id: The item ID to click
            slot_index: Specific slot index (0-27) to click. If None, clicks first found slot.
            button: Mouse button to use ('left' or 'right')
            duration: Time to take moving to the item (seconds)

        Returns:
            True if item was found and clicked, False otherwise

        Example:
            # Click first logs found
            inventory.clickItem(1511)

            # Right-click logs in slot 5
            inventory.clickItem(1511, slot_index=5, button='right')
        """
        if slot_index is not None:
            # Click specific slot
            if 0 <= slot_index < 28:
                items = self.getItemIds()
                if items[slot_index] == item_id:
                    self.slots[slot_index].click(button=button, duration=duration)
                    return True
            return False

        # Find first slot with the item
        slots = self.findItemSlots(item_id)
        if not slots:
            return False

        # Click the first slot
        self.slots[slots[0]].click(button=button, duration=duration)
        return True

    def isShiftDropEnabled(self) -> bool:
        """
        Check if shift-click drop is enabled in game settings.

        Returns:
            True if shift-drop is enabled, False otherwise

        Example:
            if inventory.isShiftDropEnabled():
                print("Shift-drop is enabled!")
        """
        from shadowlib.resources import varps

        varbit_value = varps.getVarbitByName("DESKTOP_SHIFTCLICKDROP_ENABLED")
        return varbit_value == 1

    def menuContainsDrop(self) -> bool:
        """
        Check if the right-click menu currently contains the "Drop" option.

        Returns:
            True if "Drop" is in the menu options, False otherwise

        Example:
            if inventory.menuContainsDrop():
                print("Drop option is available in the menu!")
        """
        from ..menu import Menu

        menu = Menu(self.client)
        return menu.hasOption("Drop")

    def waitDropOption(self, timeout: float = 1) -> bool:
        """
        Wait until the right-click menu contains the "Drop" option.

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            True if "Drop" option appeared within timeout, False otherwise

        Example:
            if inventory.waitDropOption(2.0):
                print("Drop option is now available!")
        """
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.menuContainsDrop():
                return True
            time.sleep(0.05)  # Small delay before checking again

        return False

    def dropItem(self, item_id: int, duration: float = 0.2, force_shift: bool = False) -> int:
        """
        Drop ALL occurrences of an item from the inventory.

        Automatically uses shift-drop if enabled in game settings,
        otherwise falls back to right-click menu.

        Args:
            item_id: The item ID to drop (drops ALL slots containing this item)
            duration: Time to take moving to each item (seconds)
            force_shift: If True, forces shift-drop even if setting is disabled

        Returns:
            Number of items dropped

        Example:
            # Drop ALL logs (auto-detects shift-drop)
            count = inventory.dropItem(1511)
            print(f"Dropped {count} logs")

            # Force shift-drop
            count = inventory.dropItem(1511, force_shift=True)

        Note:
            To drop a specific slot, use dropSlots([slot_index]) instead.
        """
        # Find all slots containing this item
        slots = self.findItemSlots(item_id)
        if not slots:
            return 0

        # Use drop_slots for the actual dropping logic
        return self.dropSlots(slots, duration=duration, force_shift=force_shift)

    def dropItems(
        self, item_ids: List[int], duration: float = 0.2, force_shift: bool = False
    ) -> int:
        """
        Drop ALL occurrences of multiple items from inventory.

        If shift-drop is enabled, holds shift for all drops (more efficient).

        Args:
            item_ids: List of item IDs to drop (drops ALL slots for each item)
            duration: Time to take moving to each item (seconds)
            force_shift: If True, forces shift-drop even if setting is disabled

        Returns:
            Total number of items dropped

        Example:
            # Drop ALL logs and ALL tinderboxes
            count = inventory.dropItems([1511, 590])
            print(f"Dropped {count} total items")

        Note:
            This drops ALL slots containing each item ID.
            To drop specific slots, use dropSlots([slot1, slot2, ...]) instead.
        """
        # Collect all slots to drop (all occurrences of all items)
        all_slots = []
        for item_id in item_ids:
            slots = self.findItemSlots(item_id)
            all_slots.extend(slots)

        if not all_slots:
            return 0

        # Use drop_slots for the actual dropping logic
        return self.dropSlots(all_slots, duration=duration, force_shift=force_shift)

    def dropSlots(
        self, slot_indices: List[int], duration: float = 0.2, force_shift: bool = False
    ) -> int:
        """
        Drop items from specific inventory slots.

        If shift-drop is enabled, holds shift for all drops (more efficient).

        Args:
            slot_indices: List of slot indices (0-27) to drop
            duration: Time to take moving to each item (seconds)
            force_shift: If True, forces shift-drop even if setting is disabled

        Returns:
            Number of slots successfully dropped

        Example:
            # Drop items in slots 12, 13, 14
            count = inventory.dropSlots([12, 13, 14])
            print(f"Dropped {count} items")

            # Drop entire inventory (all 28 slots)
            inventory.dropSlots(list(range(28)))
        """
        from shadowlib.input.io import IO

        from ..menu import Menu

        if not slot_indices:
            return 0

        # Check if shift-drop is enabled or forced
        use_shift_drop = force_shift or self.isShiftDropEnabled()

        dropped_count = 0
        io = IO()

        if use_shift_drop:
            # Hold shift for all drops
            io.keyboard.key_down("shift")

        try:
            menu = Menu(self.client)

            for slot_index in slot_indices:
                # Hover over the slot
                self.slots[slot_index].hover(duration=duration)

                # Wait for Drop option to appear in menu
                if not self.waitDropOption():
                    print("Drop option not found in menu, skipping item.")
                    continue  # Skip if Drop option not available

                # Click Drop option with fresh cache
                if menu.clickOption("Drop", duration=duration):
                    dropped_count += 1
        finally:
            if use_shift_drop:
                # Always release shift
                io.keyboard.key_up("shift")

        return dropped_count

    def selectItem(
        self, item_id: int, slot_index: Optional[int] = None, duration: float = 0.2
    ) -> bool:
        """
        Select an item in the inventory (for 'Use item on...' actions).

        Verifies the item was successfully selected using cache validation.

        Args:
            item_id: The item ID to select
            slot_index: Specific slot index (0-27) to select. If None, selects first found slot.
            duration: Time to take moving to the item (seconds)

        Returns:
            True if item was selected successfully, False otherwise

        Example:
            # Select tinderbox for use on logs
            if inventory.selectItem(590):  # Tinderbox
                print("Tinderbox selected!")
        """
        # Find the slot to click
        if slot_index is not None:
            if not (0 <= slot_index < 28):
                return False
            items = self.getItemIds()
            if items[slot_index] != item_id:
                return False
            target_slot = slot_index
        else:
            slots = self.findItemSlots(item_id)
            if not slots:
                return False
            target_slot = slots[0]

        # Click the item to select it
        self.slots[target_slot].click(button="left", duration=duration)

        # TODO: Verify selection with new cache system when implemented
        return True

    def useItemOnItem(
        self,
        item1_id: int,
        item2_id: int,
        item1_slot: Optional[int] = None,
        item2_slot: Optional[int] = None,
        duration: float = 0.2,
    ) -> bool:
        """
        Use one item on another item in inventory.

        Workflow:
        1. Select first item (left-click)
        2. Hover over second item
        3. Click menu option with '->' (e.g., 'Use Coins -> Tinderbox')

        Args:
            item1_id: The item ID to use (will be selected first)
            item2_id: The item ID to use it on (will be hovered)
            item1_slot: Specific slot for first item. If None, uses first found.
            item2_slot: Specific slot for second item. If None, uses first found.
            duration: Time to take for mouse movements (seconds)

        Returns:
            True if items were used together successfully, False otherwise

        Example:
            # Use tinderbox on logs
            inventory.useItemOnItem(590, 1511)  # Tinderbox on logs

            # Use specific slots
            inventory.useItemOnItem(995, 590, item1_slot=0, item2_slot=5)
        """
        from ..menu import Menu

        # Step 1: Select the first item
        if not self.selectItem(item1_id, slot_index=item1_slot, duration=duration):
            return False

        # Step 2: Hover over the second item
        if not self.hoverItem(item2_id, slot_index=item2_slot, duration=duration):
            return False

        # Step 3: Click the menu option with '->' in it
        menu = Menu(self.client)
        options = menu.getOptions()

        for option in options:
            if "->" in option:
                # Found the "Use X -> Y" option
                return menu.clickOption(option, duration=duration)

        return False

    def clickSlot(self, slot_index: int, button: str = "left", duration: float = 0.2) -> bool:
        """
        Click a specific inventory slot regardless of contents.

        Args:
            slot_index: Slot index (0-27) to click
            button: Mouse button to use ('left' or 'right')
            duration: Time to take moving to the slot (seconds)

        Returns:
            True if slot index is valid, False otherwise

        Example:
            # Click slot 0 (top-left)
            inventory.clickSlot(0)

            # Right-click slot 27 (bottom-right)
            inventory.clickSlot(27, button='right')
        """
        if 0 <= slot_index < 28:
            self.slots[slot_index].click(button=button, duration=duration)
            return True
        return False
