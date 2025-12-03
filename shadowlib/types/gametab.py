"""
Base GameTab class - parent class for all game tab modules.
"""

from enum import Enum

from shadowlib.globals import getClient
from shadowlib.types.box import Box


class GameTab(Enum):
    """Enum representing all game tab types in OSRS."""

    COMBAT = 0
    SKILLS = 1
    PROGRESS = 2
    INVENTORY = 3
    EQUIPMENT = 4
    PRAYER = 5
    MAGIC = 6
    GROUPING = 7
    ACCOUNT = 8
    FRIENDS = 9
    LOGOUT = 10
    SETTINGS = 11
    EMOTES = 12
    MUSIC = 13


class GameTabs:
    """
    Base class for all game tabs in Old School RuneScape.

    Each game tab (Combat, Skills, Inventory, etc.) should inherit from this class.
    Subclasses must set the TAB_TYPE class attribute to their corresponding GameTab enum.
    """

    # Subclasses must override this
    TAB_TYPE: GameTab | None = None

    def __init__(self, client=None):
        """
        Initializes a GameTab instance, setting up the Client and defining the bounds and tab areas.
            client (Optional[Any]): An optional Client instance. If None, uses the global Client.
        Attributes:
            client (Any): The Client instance used by the GameTab.
            bounds (Box): The bounding Box for the GameTab.
            tab_box_array (List[Box]): A list of Box objects representing the clickable regions for each tab.

        Args:
            client: Optional Client instance. If None, uses global Client.
        """
        self.client = client or getClient()
        x = 547
        y = 205
        w = 190
        h = 261
        self.bounds = Box(x, y, x + w, y + h)
        # init as list of Boxes for each tab
        self.tab_box_array = []

        for i in range(7):
            tab_x = 530 + (i * 33)
            tab_y = 170
            tab_w = 27
            tab_h = 32
            self.tab_box_array.append(Box(tab_x, tab_y, tab_x + tab_w, tab_y + tab_h))

        for i in range(7):
            tab_x = 530 + (i * 33)
            tab_y = 470
            tab_w = 27
            tab_h = 32
            self.tab_box_array.append(Box(tab_x, tab_y, tab_x + tab_w, tab_y + tab_h))

        # Swap index 8 and 9 because the game is weird
        self.tab_box_array[8], self.tab_box_array[9] = self.tab_box_array[9], self.tab_box_array[8]

    def getOpenTab(self) -> GameTab | None:
        """Get the currently open tab."""
        index = self.client.cache["open_tab"]
        return GameTab(index) if index in GameTab._value2member_map_ else None

    def isOpen(self) -> bool:
        """
        Check if this specific game tab is currently open.

        Returns:
            True if this tab is open, False otherwise.
        """
        if self.TAB_TYPE is None:
            raise NotImplementedError("Subclass must set TAB_TYPE class attribute")
        current_tab = self.getOpenTab()
        return current_tab == self.TAB_TYPE

    def hover(self, duration: float = 0.2) -> bool:
        """
        Hover over this specific game tab.

        Args:
            duration: Time to take moving to the tab (seconds)

        Returns:
            True if the tab area was hovered, False if TAB_TYPE not set.

        Example:
            # Hover over the inventory tab
            inventory = Inventory()
            inventory.hover()
        """
        if self.TAB_TYPE is None:
            raise NotImplementedError("Subclass must set TAB_TYPE class attribute")

        # Hover over the tab's area
        tab_area = self.tab_box_array[self.TAB_TYPE.value]
        tab_area.hover(duration=duration)

        return True

    def open(self, duration: float = 0.2) -> bool:
        """
        Open this specific game tab.

        This method hovers over the tab before clicking, then forces
        a cache update to get fresh tab state immediately.

        Args:
            duration: Time to take moving to the tab (seconds)

        Returns:
            True if the tab was successfully opened (or already open), False otherwise.

        Example:
            # Open the inventory tab
            inventory = Inventory()
            if inventory.open():
                print("Inventory tab is now open!")
        """
        if self.TAB_TYPE is None:
            raise NotImplementedError("Subclass must set TAB_TYPE class attribute")

        if self.isOpen():
            return True  # Already open

        # Click on the tab's area (which automatically hovers first)
        tab_area = self.tab_box_array[self.TAB_TYPE.value]
        tab_area.click(duration=duration)

        return waitUntil(self.isOpen, timeout=0.1, poll_interval=0.001)
