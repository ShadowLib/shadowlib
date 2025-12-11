"""
Banking module - handles all banking operations.
"""

import math
import random
from typing import List

from shadowlib.client import client
from shadowlib.types.box import Box, createGrid
from shadowlib.types.item import Item, ItemIdentifier
from shadowlib.types.itemcontainer import ItemContainer
from shadowlib.types.widget import Widget, WidgetFields
from shadowlib.utilities import timing


class BankItem:
    """Represents an item to withdraw from the bank."""

    def __init__(self, identifier: ItemIdentifier, quantity: int, noted: bool = False):
        """
        Initialize a bank item for withdrawal.

        Args:
            identifier: Item ID (int) or name (str) of the item
            quantity: The quantity to withdraw (use -1 or 0 for All)
            noted: Whether to withdraw as noted
        """
        self.identifier = identifier
        self.quantity = quantity
        self.noted = noted

    # Backwards compatibility
    @property
    def item_id(self) -> ItemIdentifier:
        """Deprecated: Use identifier instead."""
        return self.identifier


class Bank(ItemContainer):
    """
    Singleton banking operations class.

    Example:
        from shadowlib.interfaces.bank import bank

        if bank.isOpen():
            bank.depositAll()
    """

    # Expose BankItem as a class attribute for easy access
    BankItem = BankItem
    CONTAINER_ID = 95  # RuneLite bank container ID

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.containerId = self.CONTAINER_ID
        self.slotCount = 920
        self._items = []

        """Actual initialization, runs once."""
        self.deposit_all_button = Box(425, 295, 461, 331)
        self.deposit_gear_button = Box(462, 295, 498, 331)
        self.withdraw_item_button = Box(121, 310, 171, 332)
        self.withdraw_note_button = Box(172, 310, 222, 332)
        self.withdraw_1_button = Box(221, 310, 246, 332)
        self.withdraw_5_button = Box(246, 310, 271, 332)
        self.withdraw_10_button = Box(271, 310, 296, 332)
        self.withdraw_x_button = Box(296, 310, 321, 332)
        self.withdraw_all_button = Box(321, 310, 346, 332)
        self.quantity_buttons = {
            "1": self.withdraw_1_button,
            "5": self.withdraw_5_button,
            "10": self.withdraw_10_button,
            "X": self.withdraw_x_button,
            "All": self.withdraw_all_button,
        }
        self.search_button = Box(386, 295, 422, 331)
        self.settings_button = Box(467, 48, 492, 73)
        self.tab_buttons = createGrid(
            startX=62, startY=45, width=36, height=32, columns=9, rows=1, spacingX=5, spacingY=0
        )
        self.is_setup = False

        self.bank_area = Box(62, 83, 482, 293)
        self.bank_cache = {"lasttime": 0, "items": [], "quantities": []}

        self.capacity_widget = Widget(client.InterfaceID.Bankmain.CAPACITY)
        self.capacity_widget.enable(WidgetFields.getText)

        self.item_widget = Widget(client.InterfaceID.Bankmain.ITEMS)
        self.item_widget.enable(WidgetFields.getBounds)
        self.item_widget.enable(WidgetFields.isHidden)

    def __init__(self):
        """Override to prevent ItemContainer.__init__ from running."""
        pass

    @property
    def items(self) -> List[Item | None]:
        cached = client.cache.getItemContainer(self.CONTAINER_ID)
        self._items = cached.items
        return self._items

    def isOpen(self) -> bool:
        """
        Check if bank interface is open.

        Returns:
            True if bank is open, False otherwise
        """

        if client.InterfaceID.BANKMAIN in client.interfaces.getOpenInterfaces():
            if not self.is_setup:
                text = self.capacity_widget.get().get("text", None)

                if text:
                    self.slotCount = int(text)
                    self.is_setup = True
            return True

        return False

    def getOpenTab(self) -> int | None:
        """
        Get currently open bank tab.

        Returns:
            Tab index (0-8) if bank is open, None otherwise

        Example:
            tab = banking.getOpenTab()
            if tab is not None:
                print(f"Current bank tab: {tab}")
        """
        if not self.isOpen():
            return None

        return client.resources.varps.getVarbitByName("BANK_CURRENTTAB")

    def getItemcountInTab(self, tab_index: int) -> int:
        if tab_index > 8 or tab_index < 0:
            raise ValueError("tab_index must be between 0 and 8")

        if tab_index == 0:
            tabcounts = 0
            for i in range(1, 9):
                count = client.resources.varps.getVarbitByName(f"BANK_TAB_{i}")
                if count is None:
                    count = 0
                tabcounts += count
            return self.getTotalCount() - tabcounts

        return client.resources.varps.getVarbitByName(f"BANK_TAB_{tab_index}")

    def getCurrentXAmount(self) -> int:
        return client.resources.varps.getVarbitByName("BANK_REQUESTEDQUANTITY")

    def setNotedMode(self, noted: bool) -> bool:
        if not self.isOpen():
            return False

        currently_noted = client.resources.varps.getVarbitByName("BANK_WITHDRAWNOTES") > 0

        print(f"Setting noted mode to {noted}, currently {currently_noted}")

        if not currently_noted and noted:
            self.withdraw_note_button.click()

        if currently_noted and not noted:
            self.withdraw_item_button.click()

        return timing.waitUntil(
            lambda: client.resources.varps.getVarbitByName("BANK_WITHDRAWNOTES")
            == (1 if noted else 0),
            timeout=2.0,
        )

    def isSearchOpen(self) -> bool:
        if not self.isOpen():
            return False

        return client.resources.varps.getVarcValue(client.VarClientID.MESLAYERMODE) == 11

    def isXQueryOpen(self) -> bool:
        if not self.isOpen():
            return False

        return client.resources.varps.getVarcValue(client.VarClientID.MESLAYERMODE) == 7

    def getSearchText(self) -> str:
        if not self.isSearchOpen():
            return ""

        return client.resources.varps.getVarcValue(client.VarClientID.MESLAYERINPUT)

    def openSearch(self) -> bool:
        if not self.isOpen():
            return False

        if self.isSearchOpen():
            return True

        self.search_button.click()

        return self.isSearchOpen()

    def searchItem(self, text: str) -> bool:
        if not self.openSearch():
            return False

        client.input.keyboard.type(text)

        return timing.waitUntil(lambda: self.getSearchText() == text, timeout=0.5)

    def itemcountsPerTab(self):
        counts = []

        counts.append(self.getItemcountInTab(0))

        for i in range(1, 9):
            counts.append(self.getItemcountInTab(i))
        return counts

    def getIndex(self, identifier: ItemIdentifier) -> int | None:
        """
        Get the slot index of an item in the bank.

        Args:
            identifier: Item ID (int) or name (str)

        Returns:
            Slot index if found, None otherwise
        """
        if not self.containsItem(identifier):
            return None

        return self.findItemSlot(identifier)

    def getItemBox(self, identifier: ItemIdentifier) -> Box | None:
        """
        Get the bounding box of an item in the bank.

        Args:
            identifier: Item ID (int) or name (str)

        Returns:
            Box if found, None otherwise
        """
        index = self.getIndex(identifier)

        if index is None:
            return None

        result = self.item_widget.getChild(index)
        try:
            print(result)
            if result["isHidden"]:
                return None
            rectdata = result["bounds"]
            return Box(
                rectdata[0],
                rectdata[1],
                rectdata[0] + rectdata[2],
                rectdata[1] + rectdata[3],
            )
        except Exception as e:
            print(f"Error getting item area: {e}")
            return None

    def isBoxClickable(self, box: Box) -> bool:
        return 83 <= box.y1 <= 257

    def getScrollCount(self, box: Box) -> tuple[int, bool]:
        """
        Returns:
            (scroll_count, scroll_up)
            scroll_up = True  -> your 'scroll up' gesture (increases y1 by +45 per scroll)
            scroll_up = False -> 'scroll down' gesture (decreases y1 by -45 per scroll)
        """
        step = 45
        min_y, max_y = 83, 257
        y = box.y1

        # Already visible
        if 83 <= y <= 257:
            return 0, False  # direction irrelevant

        if y < min_y:
            # Need to INCREASE y -> scroll_up
            scroll_up = True
            k_min = math.ceil((min_y - y) / step)  # smallest k so y + k*step >= 83
            k_max = math.floor((max_y - y) / step)  # largest  k so y + k*step <= 257
            if k_max < k_min:
                k_max = k_min  # safety
            k = random.randint(k_min, k_max)
            return k, scroll_up

        else:  # y > max_y
            # Need to DECREASE y -> scroll_down
            scroll_up = False
            k_min = math.ceil((y - max_y) / step)  # smallest k so y - k*step <= 257
            k_max = math.floor((y - min_y) / step)  # largest  k so y - k*step >= 83
            if k_max < k_min:
                k_max = k_min  # safety
            k = random.randint(k_min, k_max)
            return k, scroll_up

    def makeItemVisible(self, identifier: ItemIdentifier) -> Box | None:
        """
        Scroll the bank view to make an item visible and clickable.

        Args:
            identifier: Item ID (int) or name (str)

        Returns:
            Box if item is now visible, None otherwise
        """
        if not self.containsItem(identifier):
            raise ValueError("Item not found in bank")

        box = self.getItemBox(identifier)

        if box is None:
            tab_index = self.getTabIndex(identifier)
            if tab_index is None:
                return None
            if not self.openTab(tab_index):
                return None
            box = self.getItemBox(identifier)

        scroll_count, scroll_up = self.getScrollCount(box)

        if scroll_count != 0:
            self.bank_area.hover()

            client.input.mouse.scroll(up=scroll_up, count=scroll_count)
            timing.sleep(0.05)

            # Verify visibility
            box = self.getItemBox(identifier)

        print(f"found box: {box}")

        if self.isBoxClickable(box):
            return box
        else:
            return None

    def getTabIndex(self, identifier: ItemIdentifier) -> int | None:
        """
        Get the bank tab index containing an item.

        Args:
            identifier: Item ID (int) or name (str)

        Returns:
            Tab index (0-8) if found, None otherwise
        """
        index = self.getIndex(identifier)

        if index is None:
            return None

        tabcounts = self.itemcountsPerTab()

        cumcount = 0
        for i in range(1, 0):
            cumcount += tabcounts[i]
            if index < cumcount:
                return i

        return None

    def openTab(self, tab_index: int) -> bool:
        """
        Open a specific bank tab.

        Args:
            tab_index: Index of the tab to open (0-8)

        Returns:
            True if successful, False otherwise

        Example:
            banking.openTab(2)  # Open bank tab 2
        """
        if not self.isOpen():
            return False

        if tab_index < 0 or tab_index > 8:
            raise ValueError("tab_index must be between 0 and 8")

        if self.getOpenTab() == tab_index:
            return True

        self.tab_buttons[tab_index].click()

        return timing.waitUntil(lambda: self.getOpenTab() == tab_index, timeout=2.0)

    def setWithdrawQuantity(self, quantity: str, wait: bool = True) -> bool:
        """
        Set the withdraw quantity mode.

        Args:
            quantity: One of '1', '5', '10', 'X', 'All'

        Returns:
            True if successful, False otherwise

        Example:
            banking.setWithdrawQuantity('10')  # Set withdraw mode to 10
        """
        if not self.isOpen():
            return False

        allowed = ["1", "5", "10", "X", "All"]

        if quantity not in allowed:
            raise ValueError("quantity must be one of '1', '5', '10', 'X', 'All'")

        index = allowed.index(quantity)

        self.quantity_buttons[quantity].click()

        if not wait:
            return True

        return timing.waitUntil(
            lambda: client.resources.varps.getVarbitByName("BANK_QUANTITY_TYPE") == index, timeout=1
        )

    def checkItemsDeposited(self, start_count) -> bool:
        current_count = client.tabs.inventory.getTotalQuantity()
        print(f"start count: {start_count}, current count: {current_count}")
        return current_count < start_count

    def depositAll(self, wait: bool = True) -> bool:
        """
        Deposit all items in inventory.

        Returns:
            True if successful, False otherwise
        """
        if not self.isOpen():
            return False

        start = client.tabs.inventory.getTotalQuantity()

        if start == 0:
            return True  # Nothing to deposit

        self.deposit_all_button.click()

        if not wait:
            return True

        return timing.waitUntil(lambda: self.checkItemsDeposited(start), timeout=2.0)

    def depositEquipment(self, wait: bool = True) -> bool:
        """
        Deposit all worn equipment.

        Returns:
            True if successful, False otherwise

        Example:
            if banking.isOpen():
                banking.depositEquipment()
        """
        if not self.isOpen():
            return False

        start = client.tabs.equipment.getTotalCount()

        self.deposit_gear_button.click()

        if not wait:
            return True

        return timing.waitUntil(lambda: client.tabs.equipment.getTotalCount() < start, timeout=2.0)

    def withdrawItems(self, bank_items: list[BankItem], safe: bool = True) -> bool:
        """
        Withdraw multiple items from the bank.

        Args:
            bank_items: List of BankItem objects specifying what to withdraw
            safe: If True, raises ValueError when item not found

        Returns:
            True if all items withdrawn successfully

        Example:
            bank.withdrawItems([
                BankItem(995, 1000),              # 1000 coins by ID
                BankItem("Lobster", 5),           # 5 lobsters by name
                BankItem("Dragon bones", 28, noted=True)  # 28 noted dragon bones
            ])
        """
        if not self.isOpen():
            return False

        for bank_item in bank_items:
            identifier = bank_item.identifier
            quantity = bank_item.quantity
            noted = bank_item.noted

            if not self.containsItem(identifier):
                if safe:
                    raise ValueError(f"Item {identifier} not found in bank!")
                return False

            slot = self.findItemSlot(identifier)
            if slot is not None and self.items[slot].quantity < quantity:
                if safe:
                    raise ValueError(f"Not enough quantity of {identifier} in bank!")
                return False

            if not self.isOpen():
                return False

            area = self.makeItemVisible(identifier)

            self.setNotedMode(noted)

            if area is None:
                return False

            area.hover()
            client.interactions.menu.waitHasOption("Withdraw")

            if quantity == 1:
                client.interactions.menu.clickOption("Withdraw-1")
            elif quantity == 5:
                client.interactions.menu.clickOption("Withdraw-5")
            elif quantity == 10:
                client.interactions.menu.clickOption("Withdraw-10")
            elif quantity <= 0:
                client.interactions.menu.clickOption("Withdraw-All")
            elif self.getCurrentXAmount() == quantity:
                client.interactions.menu.clickOption(f"Withdraw-{quantity}")
            else:
                client.interactions.menu.clickOption("Withdraw-X")
                timing.waitUntil(lambda: self.isXQueryOpen(), timeout=3.0)
                client.input.keyboard.type(str(quantity))
                client.input.keyboard.pressEnter()

        return True

    def withdrawItem(self, bank_item: BankItem, safe: bool = True) -> bool:
        """
        Withdraw a single item from the bank.

        Args:
            bank_item: BankItem specifying what to withdraw
            safe: If True, raises ValueError when item not found

        Returns:
            True if item withdrawn successfully

        Example:
            bank.withdrawItem(BankItem(995, 1000))           # By ID
            bank.withdrawItem(BankItem("Lobster", 5))        # By name
        """
        return self.withdrawItems([bank_item], safe=safe)


# Module-level singleton instance
bank = Bank()
