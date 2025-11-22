"""
Banking module - handles all banking operations.
"""

import math
import random
from typing import Optional

import src
from src.utils import timing

from shadowlib.globals import getClient
from shadowlib.utilities.geometry import Area, createGrid


class BankItem:
    """Represents an item in the bank."""

    def __init__(self, item_id: int, quantity: int, noted: bool = False):
        """
        Initialize a bank item.

        Args:
            item_id: The ID of the item.
            quantity: The quantity of the item.
        """
        self.item_id = item_id
        self.quantity = quantity
        self.noted = noted


class Bank:
    """Banking operations class."""

    # Expose BankItem as a class attribute for easy access
    BankItem = BankItem

    def __init__(self, client=None):
        """
        Initialize banking manager.

        Args:
            client: Optional Client instance. If None, uses global Client.
        """
        self.client = client or getClient()
        self.deposit_all_button = Area(425, 295, 461, 331)
        self.deposit_gear_button = Area(462, 295, 498, 331)
        self.withdraw_item_button = Area(121, 310, 171, 332)
        self.withdraw_note_button = Area(172, 310, 222, 332)
        self.withdraw_1_button = Area(221, 310, 246, 332)
        self.withdraw_5_button = Area(246, 310, 271, 332)
        self.withdraw_10_button = Area(271, 310, 296, 332)
        self.withdraw_x_button = Area(296, 310, 321, 332)
        self.withdraw_all_button = Area(321, 310, 346, 332)
        self.quantity_buttons = {
            "1": self.withdraw_1_button,
            "5": self.withdraw_5_button,
            "10": self.withdraw_10_button,
            "X": self.withdraw_x_button,
            "All": self.withdraw_all_button,
        }
        self.search_button = Area(386, 295, 422, 331)
        self.settings_button = Area(467, 48, 492, 73)
        self.tab_buttons = createGrid(62, 45, 36, 32, 9, 1, 5, 0)
        self.is_setup = False
        self.capacity = 920
        self.bank_area = Area(62, 83, 482, 293)
        self.bank_cache = {"lasttime": 0, "items": [], "quantities": []}

    def isOpen(self) -> bool:
        """
        Check if bank interface is open.

        Returns:
            True if bank is open, False otherwise
        """

        if self.client.interfaces.is_id_open(src.InterfaceID.Bankmain.INFINITE):
            if not self.is_setup:
                q = self.client.query()
                cap = q.client.getWidget(src.InterfaceID.Bankmain.CAPACITY).getText()
                result = q.execute({"capacity": cap})
                try:
                    capstr = result["results"]["capacity"]
                    self.capacity = int(capstr)
                    self.is_setup = True
                except Exception as e:
                    print(f"Error setting up bank capacity: {e}")
            return True

        print("Bank is not open")
        return False

    def _updateCache(self, max_age=5):
        """
        Update bank item cache if older than max_age ticks.
        Args:
            max_age: Maximum age of cache in ticks (default 5)
        """

        if (
            self.bank_cache["lasttime"] == 0
            or self.bank_cache["lasttime"] + max_age < timing.current_tick()
        ):
            q = self.client.query()
            bank = q.client.getItemContainer(self.client.api.InventoryID.BANK)
            items = bank.getItems()
            ids = q.forEach(items, lambda item: item.getId())
            quantities = q.forEach(items, lambda item: item.getQuantity())
            result = q.execute({"ids": ids, "quantities": quantities})
            try:
                idlist = result["results"]["ids"]
                quantitylist = result["results"]["quantities"]
                self.bank_cache["items"] = idlist
                self.bank_cache["quantities"] = quantitylist
                self.bank_cache["lasttime"] = timing.current_tick()
            except Exception as e:
                print(f"Error getting bank items: {e}")

        return self.bank_cache

    def getAllItems(self, max_age=5):
        """
        Get all items in bank, with caching.

        Args:
            max_age: Maximum age of cache in ticks (default 5)
        """
        cache = self._updateCache(max_age)
        return cache["items"], cache["quantities"]

    def getOpenTab(self) -> Optional[int]:
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

        return self.client.varps.getVarbitByName("BANK_CURRENTTAB")

    def getItemcountInTab(self, tab_index: int) -> int:
        if tab_index > 8 or tab_index < 0:
            raise ValueError("tab_index must be between 0 and 8")

        items, _ = self.getAllItems()

        if tab_index == 0:
            for i in range(1, 9):
                count = self.client.varps.getVarbitByName(f"BANK_TAB_{i}")
                if count is None:
                    count = 0
                tabcounts += count
            return len(items) - tabcounts

        return self.client.varps.getVarbitByName(f"BANK_TAB_{tab_index}")

    def getCurrentXAmount(self) -> int:
        return self.client.varps.getVarbitByName("BANK_REQUESTEDQUANTITY")

    def setNotedMode(self, noted: bool) -> bool:
        if not self.isOpen():
            return False

        currently_noted = self.client.varps.getVarbitByName("BANK_WITHDRAWNOTES") > 0

        print(f"Setting noted mode to {noted}, currently {currently_noted}")

        if not currently_noted and noted:
            self.withdraw_note_button.click()

        if currently_noted and not noted:
            self.withdraw_item_button.click()

        return timing.wait_until(
            lambda: self.client.varps.getVarbitByName("BANK_WITHDRAWNOTES") == (1 if noted else 0),
            timeout=2.0,
        )

    def isSearchOpen(self) -> bool:
        if not self.isOpen():
            return False

        # TODO: Update when new cache system is implemented
        # For now, query directly
        q = self.client.query()
        mode = q.client.getVarbitValue(6590)  # MESLAYERMODE varbit
        result = q.execute({"mode": mode})
        return result.get("mode") == 11

    def isXQueryOpen(self) -> bool:
        if not self.isOpen():
            return False

        # TODO: Update when new cache system is implemented
        # For now, query directly
        q = self.client.query()
        mode = q.client.getVarbitValue(6590)  # MESLAYERMODE varbit
        result = q.execute({"mode": mode})
        return result.get("mode") == 7

    def getSearchText(self) -> str:
        if not self.isSearchOpen():
            return ""

        q = self.client.query()
        search = q.client.getVarcStrValue(src.VarClientID.MESLAYERINPUT)
        result = q.execute({"search": search})
        try:
            searchstr = result["results"]["search"]
            return searchstr
        except Exception as e:
            print(f"Error getting bank search text: {e}")
            return ""

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

        self.client.io.keyboard.type_text(text, delay=0.05)

        return True

    def itemcountsPerTab(self):
        counts = []

        counts.append(self.getItemcountInTab(0))

        for i in range(1, 9):
            counts.append(self.getItemcountInTab(i))
        return counts

    def getIndex(self, item_id: int) -> Optional[int]:
        items, _ = self.getAllItems()

        if item_id not in items:
            return None

        return items.index(item_id)

    def getItemArea(self, item_id: int) -> Optional[Area]:
        index = self.getIndex(item_id)

        if index is None:
            return None

        q = self.client.query()
        items = q.client.getWidget(src.InterfaceID.Bankmain.ITEMS).getDynamicChildren()
        item = items[index]
        rect = item.getBounds()
        hidden = item.isHidden()
        result = q.execute({"rect": rect, "hidden": hidden})
        try:
            if result["results"]["hidden"]:
                return None
            rectdata = result["results"]["rect"]
            return Area(
                rectdata["x"],
                rectdata["y"],
                rectdata["x"] + rectdata["width"],
                rectdata["y"] + rectdata["height"],
            )
        except Exception as e:
            print(f"Error getting item area: {e}")
            return None

    def isAreaClickable(self, area: Area) -> bool:
        return 83 <= area.y1 <= 257

    def getScrollCount(self, area: Area) -> tuple[int, bool]:
        """
        Returns:
            (scroll_count, scroll_up)
            scroll_up = True  -> your 'scroll up' gesture (increases y1 by +45 per scroll)
            scroll_up = False -> 'scroll down' gesture (decreases y1 by -45 per scroll)
        """
        step = 45
        min_y, max_y = 83, 257
        y = area.y1

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

    def makeItemVisible(self, item_id: int) -> Optional[Area]:
        items, quantities = self.getAllItems()

        if item_id not in items:
            raise ValueError("Item not found in bank")

        area = self.getItemArea(item_id)

        if area is None:
            print("Opening correct tab for item...")
            tab_index = self.getTabIndex(item_id)
            if tab_index is None:
                return None
            if not self.openTab(tab_index):
                return None
            area = self.getItemArea(item_id)

        scroll_count, scroll_up = self.getScrollCount(area)

        if scroll_count != 0:
            print(
                f"Scrolling {'up' if scroll_up else 'down'} {scroll_count} times to make item visible..."
            )
            self.bank_area.hover()

            if scroll_up:
                self.client.io.mouse.scroll_up(scroll_count)
            else:
                self.client.io.mouse.scroll_down(scroll_count)
            timing.sleep(0.2)

            # Verify visibility
            area = self.getItemArea(item_id)

        print(f"found area: {area}")

        if self.isAreaClickable(area):
            return area
        else:
            return None

    def getTabIndex(self, item_id: int) -> Optional[int]:
        index = self.getIndex(item_id)

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

        return timing.wait_until(lambda: self.getOpenTab() == tab_index, timeout=2.0)

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

        return timing.wait_until(
            lambda: self.client.varps.getVarbitByName("BANK_QUANTITY_TYPE") == index, timeout=2.0
        )

    def checkItemsDeposited(self, start_count) -> bool:
        current_count = self.client.inventory.totalQuantity()
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

        start = self.client.inventory.totalQuantity()

        if start == 0:
            return True  # Nothing to deposit

        self.deposit_all_button.click()

        if not wait:
            return True

        return timing.wait_until(lambda: self.checkItemsDeposited(start), timeout=2.0)

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

        start = len(self.client.equipment.getItemIds())

        self.deposit_gear_button.click()

        if not wait:
            return True

        return timing.wait_until(
            lambda: len(self.client.equipment.getItemIds()) < start, timeout=2.0
        )

    def withdrawItems(self, bank_items: list[BankItem], safe: bool = True) -> bool:
        for bank_item in bank_items:
            item_id = bank_item.item_id
            quantity = bank_item.quantity
            noted = bank_item.noted

            print(f"Withdrawing {quantity} of item ID {item_id} (noted={noted})")

            items, quantities = self.getAllItems(0)

            if item_id not in items:
                print(f"Item ID {item_id} not found in bank!")
                if safe:
                    raise ValueError(f"Item ID {item_id} not found in bank!")
                return False

            if quantities[items.index(item_id)] < quantity:
                print(f"Not enough quantity of item ID {item_id} in bank!")
                if safe:
                    raise ValueError(f"Not enough quantity of item ID {item_id} in bank!")
                return False

            if not self.isOpen():
                print("Bank is not open!")
                return False

            area = self.makeItemVisible(item_id)

            self.setNotedMode(noted)

            if area is None:
                print(f"Item ID {item_id} not found in bank!")
                return False

            area.hover()

            if quantity == 1:
                self.client.menu.clickOption("Withdraw-1")
            elif quantity == 5:
                self.client.menu.clickOption("Withdraw-5")
            elif quantity == 10:
                self.client.menu.clickOption("Withdraw-10")
            elif quantity <= 0:
                self.client.menu.clickOption("Withdraw-All")
            elif self.getCurrentXAmount() == quantity:
                self.client.menu.clickOption(f"Withdraw-{quantity}")
            else:
                self.client.menu.clickOption("Withdraw-X")
                timing.wait_until(lambda: self.isXQueryOpen(), timeout=3.0)
                self.client.io.keyboard.type_text(str(quantity))
                self.client.io.keyboard.press_enter()

            # Wait for item to appear in inventory
            def checkWithdrawal():
                inv_count = self.client.inventory.totalQuantity()
                return inv_count >= quantity and inv_count > 0

            if not timing.wait_until(check_withdrawal, timeout=5.0):
                print(f"Failed to withdraw item ID {item_id}!")
                return False

    def withdrawItem(self, bank_item: BankItem, safe: bool = True) -> bool:
        return self.withdrawItems([bank_item], safe=safe)
