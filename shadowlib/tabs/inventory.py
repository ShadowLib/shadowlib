"""
Inventory tab module.
"""

from typing import Any, Dict, List, Optional

from shadowlib.types.gametab import GameTab, GameTabs
from shadowlib.types.item import Item
from shadowlib.types.itemcontainer import ItemContainer
from shadowlib.types.box import createGrid, Box
from shadowlib.utilities.item_names import getFormattedItemName, getItemName


class Inventory(GameTabs, ItemContainer):
    """
    Inventory operations class combining GameTab and ItemContainer functionality.
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
        # Initialize GameTabs (which sets up client and tab areas)
        GameTabs.__init__(self, client)
        # Initialize ItemContainer with inventory-specific values
        ItemContainer.__init__(self, containerId=self.INVENTORY_ID, slotCount=28, items=[])

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

    @property
    def items(self):
        """Auto-sync items from cache when accessed."""
        cached = self.client.cache.getItemContainer(self.INVENTORY_ID)
        self._items = cached.items
        return self._items
    
    def getSlotBox(self, slot_index: int) ->  Box:
        """
        Get the Box area for a specific inventory slot.

        Args:
            slot_index: Slot index (0-27)
        Returns:
            Box area of the specified slot
        """
        return self.slots[slot_index]
    
    def hoverSlot(self, slot_index: int) -> bool:
        """
        Hover over a specific inventory slot regardless of contents.

        Args:
            slot_index: Slot index (0-27) to hover

        Returns:
            True if slot index is valid, False otherwise

        Example:
            # Hover over slot 0 (top-left)
            inventory.hoverSlot(0)

            # Hover over slot 27 (bottom-right)
            inventory.hoverSlot(27)
        """
        if 0 <= slot_index < 28:
            self.getSlotBox(slot_index).hover()
            return True
        return False

    def hoverItem(self, item_id: int, random: bool = False) -> bool:
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
        if not random:
            # Find first slot with the item
            slot = self.findItemSlot(item_id)
            if slot is None:
                return False

            # Hover the first slot
            self.slots[slot].hover()
            return True

        found_slots = self.findItemSlots(item_id)
        selected_slot = random.choice(found_slots) if found_slots else None
        if selected_slot is None:
            return False

        # Hover the first slot
        self.slots[selected_slot].hover()
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
            self.slots[slot_index].hover()
            return True
        return False
    
    def clickSlot(self, slot_index: int) -> bool:
        """
        Click a specific inventory slot regardless of contents.

        Args:
            slot_index: Slot index (0-27) to click

        Returns:
            True if slot index is valid, False otherwise

        Example:
            # Click slot 0 (top-left)
            inventory.clickSlot(0)

            # Click slot 27 (bottom-right)
            inventory.clickSlot(27)
        """
        if self.hoverSlot(slot_index):
            # self.client.input.mouse.leftClick()
            return True
        return False

    def clickItem(
        self,
        item_id: int,
        slot_index: int | None = None,
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
            if 0 <= slot_index < 28 and self.hoverSlot(slot_index):
                items = self.getItemIds()
                if items[slot_index] == item_id:
                    self.slots[slot_index].click(button=button)
                    return True
            return False

        # Find first slot with the item
        slots = self.findItemSlots(item_id)
        if not slots:
            return False

        # Click the first slot
        self.slots[slots[0]].click(button=button, )
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
        from shadowlib._internal.resources import varps

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
        return self.dropSlots(slots, , force_shift=force_shift)

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
        return self.dropSlots(all_slots, , force_shift=force_shift)

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
                self.slots[slot_index].hover()

                # Wait for Drop option to appear in menu
                if not self.waitDropOption():
                    print("Drop option not found in menu, skipping item.")
                    continue  # Skip if Drop option not available

                # Click Drop option with fresh cache
                if menu.clickOption("Drop", ):
                    dropped_count += 1
        finally:
            if use_shift_drop:
                # Always release shift
                io.keyboard.key_up("shift")

        return dropped_count

    def selectItem(
        self, item_id: int, slot_index: int | None = None, duration: float = 0.2
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
        self.slots[target_slot].click(button="left", )

        # TODO: Verify selection with new cache system when implemented
        return True

    def useItemOnItem(
        self,
        item1_id: int,
        item2_id: int,
        item1_slot: int | None = None,
        item2_slot: int | None = None,
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
        if not self.selectItem(item1_id, slot_index=item1_slot, ):
            return False

        # Step 2: Hover over the second item
        if not self.hoverItem(item2_id, slot_index=item2_slot, ):
            return False

        # Step 3: Click the menu option with '->' in it
        menu = Menu(self.client)
        options = menu.getOptions()

        for option in options:
            if "->" in option:
                # Found the "Use X -> Y" option
                return menu.clickOption(option, )

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
            self.slots[slot_index].click(button=button, )
            return True
        return False
