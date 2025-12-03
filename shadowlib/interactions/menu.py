"""
Menu module - handles right-click context menu interactions.
"""

import math
import time
from copy import deepcopy
from typing import List, Tuple

from shadowlib.globals import getClient
from shadowlib.utilities.text import stripColorTags
from shadowlib.utilities import timing

from shadowlib.types import Box



class Menu:
    """
    Menu operations class for handling right-click context menus.
    """

    def __init__(self):
        """
        Initialize menu manager.

        Args:
            client: Optional Client instance. If None, uses global Client.
        """
        self.client = getClient()

    def isOpen(self) -> bool:
        """
        Check if the right-click context menu is currently open.

        Reads from game state cache (updated every tick).

        Returns:
            True if menu is open, False otherwise
        """
        
        return self.client.cache.getClientTickState().get("menu_open", False)
    
    def _getOptions(self, strip_colors: bool = True) -> Tuple[List[str], List[str]]:
        data = deepcopy(self.client.cache.getMenuOptions())
        types = data["types"]
        options = data["options"]
        targets = data["targets"]

        if not types or not options or not targets:
            return [], []
        
        # Combine types, options, and targets into formatted strings
        
        formatted_options = [f"{option} {target}".strip() for option, target in zip(options, targets)]
        if strip_colors:
            formatted_options = [stripColorTags(opt) for opt in formatted_options]

        # reverse because they're stored backwards (last item is first option)
        formatted_options.reverse()
        types.reverse()

        return formatted_options, types
    
    def _getMenuInfo(self) -> dict:
        return self.client.cache.getMenuState()     

    def waitMenuClickEvent(self, max_age: float = 0.2, timeout: float = 0.5) -> bool:
        """
        Wait for a menu option click event to be registered in the cache.

        Args:
            timeout: Maximum time to wait for event (seconds). if time since last click is less than timeout, returns True immediately.

        Returns:
            True if event detected, False if timeout
        """
        current_state = self.client.cache.getMenuClickedState()
        timestamp = current_state.get("_timestamp", 0)

        if (time.time() - timestamp) < max_age:
            return True

        def check_event(timestamp) -> bool:
            state = self.client.cache.getMenuClickedState()
            event_time = state.get("_timestamp", 0)
            return (event_time - ts) > 0

        return timing.waitUntil(lambda: checkEvent(timestamp), timeout=timeout, poll_interval=0.001)

    def waitHasType(self, option_type: str, timeout: float = 0.5) -> bool:
        """
        Wait until the menu contains an option of the specified type.

        Args:
            option_type: Type to search for in menu options (e.g., "WIDGET_TARGET")
            timeout: Maximum time to wait for option type to appear (seconds)
        Returns:
            True if option type found, False if timeout
        """

        def checkType() -> bool:
            return self.hasType(option_type)

        return timing.waitUntil(checkType, timeout=timeout, poll_interval=0.001)

    def waitHasOption(self, option: str, timeout: float = 0.5) -> bool:
        """
        Wait until the menu contains an option of the specified type.

        Args:
            option: Text to search for in menu options (e.g., "Drop")
            timeout: Maximum time to wait for option to appear (seconds)
        Returns:
            True if option found, False if timeout
        """

        def checkOption() -> bool:
            return self.hasOption(option)

        return timing.waitUntil(checkOption, timeout=timeout, poll_interval=0.001)

    def open(self, timeout: float = 0.5) -> bool:
        """
        Open the context menu by right-clicking at current mouse position.

        Waits until menu is confirmed open via cache (5ms polling).

        Args:
            timeout: Maximum time to wait for menu to open (seconds)

        Returns:
            True if menu opened successfully, False otherwise

        Example:
            menu = Menu()
            if menu.open():
                menu.clickOption("Drop")
        """
        if self.isOpen():
            return True  # Already open
        
        # Right-click at current position
        self.client.input.mouse.rightClick()

        # Wait for menu to open
        return timing.waitUntil(self.isOpen, timeout=timeout, poll_interval=0.001)

    def close(self, use_cancel: bool = True, timeout: float = 1.0) -> bool:
        """
        Close the context menu.

        Strategy:
        - If menu not open: returns True immediately
        - If scrollable menu: always moves mouse away (ignore use_cancel)
        - If use_cancel=True: clicks "Cancel" option
        - If use_cancel=False: moves mouse 30+ pixels away from menu

        After closing action, waits until menu state confirms it's closed.

        Args:
            use_cancel: If True, click Cancel option. If False, move mouse away.
                       Ignored for scrollable menus (always uses mouse move).
            timeout: Maximum time to wait for menu to close (seconds)

        Returns:
            True if menu closed successfully, False otherwise

        Example:
            # Close by clicking Cancel
            menu.close(use_cancel=True)

            # Close by moving mouse away
            menu.close(use_cancel=False)
        """
        import random

        # Check if menu is open
        if not self.isOpen():
            return True  # Already closed

        state = self._getMenuInfo()
        # Get menu state from cache
        scrollable = state.get("scrollable", False)
        menu_x = state.get("menuX", 0)
        menu_y = state.get("menuY", 0)
        menu_width = state.get("width", 0)
        menu_height = state.get("height", 0)

        # For scrollable menus, always move mouse away
        if scrollable:
            use_cancel = False

        if use_cancel and not scrollable:
            # Click Cancel option
            options = self.getOptions()
            cancel_index = None

            for i, option in enumerate(options):
                if "cancel" in option.lower():
                    cancel_index = i
                    break

            if cancel_index is not None:
                box = self.getOptionBox(cancel_index)
                if box:
                    box.click()
            else:
                # Cancel not found, fall back to mouse move
                use_cancel = False

        if not use_cancel:
            # Move mouse at least 30 pixels away from menu box
            menu_x1 = menu_x
            menu_y1 = menu_y
            menu_x2 = menu_x + menu_width
            menu_y2 = menu_y + menu_height

            # Pick a random direction and move 30-50 pixels away
            distance = random.randint(30, 50)

            # Randomly choose a direction: up, down, left, or right
            direction = random.choice(["up", "down", "left", "right"])

            if direction == "up":
                target_x = random.randint(menu_x1, menu_x2)
                target_y = menu_y1 - distance
            elif direction == "down":
                target_x = random.randint(menu_x1, menu_x2)
                target_y = menu_y2 + distance
            elif direction == "left":
                target_x = menu_x1 - distance
                target_y = random.randint(menu_y1, menu_y2)
            else:  # right
                target_x = menu_x2 + distance
                target_y = random.randint(menu_y1, menu_y2)

            # Move mouse to target position
            self.client.input.mouse.moveTo(target_x, target_y, safe = False)

            return timing.waitUntil(lambda: not self.isOpen(), timeout=timeout, poll_interval=0.001)

    def getOptions(self, strip_colors: bool = True) -> List[str]:
        """
        Get all menu options as formatted strings.

        Reads from game state cache (updated every tick).

        The menu_options contains pairs of [option, target] strings.
        These are combined with a space and returned in the order they appear
        on the menu (reversed, since last item in array is first menu option).

        Args:
            strip_colors: If True, removes color tags like <col=ffffff> (default: True)

        Returns:
            List of menu option strings in display order (top to bottom)

        Example:
            options = menu.getOptions()
            # ['Drop Logs', 'Use Logs', 'Follow Player  (level-99)']
        """
        menu_options, _ = self._getOptions(strip_colors=strip_colors)

        return menu_options
    
    def getTypes(self) -> List[str]:
        """
        Get all menu option types.

        Reads from game state cache (updated every tick).

        The menu option types correspond to the action types for each option.

        Returns:
            List of menu option types in display order (top to bottom)
        """
        _, menu_types = self._getOptions(strip_colors=True)

        return menu_types


    def getLeftClickOption(self, strip_colors: bool = True) -> str | None:
        """
        Get the default menu option (the one accessible with left-click).

        The default option is the first option displayed on the menu,
        which is the LAST item in the menu_options array.

        Args:
            strip_colors: If True, removes color tags (default: True)

        Returns:
            The default option string, or None if no options available

        Example:
            default = menu.getDefaultOption()
            # "Eat Shark" (if that's the first option on the menu)
        """
        options = self.getOptions(strip_colors=strip_colors)
        if not options:
            return None

        return options[0]
    
    def getLeftClickType(self) -> str | None:
        """
        Get the action type of the default menu option (the one accessible with left-click).

        The default option is the first option displayed on the menu,
        which is the LAST item in the menu_types array.

        Returns:
            The default option type string, or None if no options available
        """
        types = self.getTypes()
        if not types:
            return None

        return types[0]
        

    def hasOption(self, option_text: str, strip_colors: bool = True) -> bool:
        """
        Check if a menu option exists (partial matching, case-insensitive).

        Reads from game state cache (updated every tick).

        Args:
            option_text: Text to search for in menu options (e.g., "Drop")
            strip_colors: If True, removes color tags before matching (default: True)

        Returns:
            True if option exists, False otherwise
        """
        options = self.getOptions(strip_colors=strip_colors)
        option_text_lower = option_text.lower()

        return any(option_text_lower in option.lower() for option in options)

    def hasType(self, option_type: str) -> bool:
        """
        Check if a menu option of a specific type exists (partial matching, case-insensitive).

        Reads from game state cache (updated every tick).

        Args:
            option_type: Type to search for in menu options (e.g., "WIDGET_TARGET")

        Returns:
            True if option type exists, False otherwise
        """
        types = self.getTypes()
        option_type_lower = option_type.lower()
        print("checking for type:", option_type_lower, "in", types)  # --- IGNORE ---
        return any(option_type_lower in t.lower() for t in types)

    def getOptionBox(self, option_index: int) -> Box | None:
        """
        Get the clickable box for a specific menu option.

        Menu option boxes are calculated based on:
        - Menu position (menuX, menuY)
        - Offset: (2, 19) from menu position to first option
        - Each option: (menuWidth - 4) wide, 15 pixels total height
        - Options stack vertically with no overlap

        Args:
            option_index: Index of the option (0 = first/top option)

        Returns:
            Box object for the option, or None if invalid index

        Example:
            box = menu.getOptionBox(0)  # Get first option's box
            if box:
                box.click()
        """
        if not self.isOpen():
            return None

        options = self.getOptions()
        if not options or option_index < 0 or option_index >= len(options):
            return None

        state = self._getMenuInfo()

        # Get menu position and dimensions
        menu_x = state.get("menuX", 0)
        menu_y = state.get("menuY", 0)
        menu_width = state.get("width", 0)

        # First option starts at offset (2, 19) from menu position
        option_x1 = menu_x + 2
        option_y1 = menu_y + 19 + (option_index * 15)

        # Each option is (menuWidth - 4) wide and spans 15 pixels
        # Using x2 = x1 + width - 1 to avoid overlap (e.g., 100-114 = 15 pixels)
        option_x2 = option_x1 + (menu_width - 4) - 1
        option_y2 = option_y1 + 14  # 15 pixels total: y1 to y1+14 inclusive

        return Box(option_x1, option_y1, option_x2, option_y2)

    def hoverOption(self, option_text: str) -> bool:
        """
        Hover over a menu option by matching text.

        Automatically opens menu if not already open.

        Args:
            option_text: Text to search for in menu options (e.g., "Drop", "Use")

        Returns:
            True if option was found and hovered, False otherwise
        """
        # Ensure menu is open
        if not self.open():
            return False

        options = self.getOptions()
        option_text_lower = option_text.lower()

        for i, option in enumerate(options):
            if option_text_lower in option.lower():
                box = self.getOptionBox(i)
                if box:
                    box.hover()
                    return True

        return False

    def hoverOptionIndex(self, option_index: int) -> bool:
        """
        Hover over a menu option by its index.

        Automatically opens menu if not already open.

        Args:
            option_index: Index of the option (0 = first/top option)

        Returns:
            True if option was hovered, False if invalid index

        Example:
            # Hover over the first menu option (opens menu if needed)
            menu.hoverOptionIndex(0)
        """
        # Ensure menu is open
        if not self.open():
            return False

        box = self.getOptionBox(option_index)
        if box:
            box.hover()
            return True
        return False
    
    def lastOptionClicked(self) -> str:
        latest_click = self.client.cache.getMenuClickedState()
        option = latest_click.get("menu_option", "")
        target = latest_click.get("menu_target", "")
        full_option = f"{option} {target}".strip()
        return stripColorTags(full_option)
    
    def waitOptionClicked(self, option_text: str, max_age: float = 0.2, timeout: float = 0.5) -> bool:
        if not self.waitMenuClickEvent(max_age=max_age, timeout=timeout):
            return False

        return option_text.lower() in self.lastOptionClicked().lower()

    def clickOption(self, option_text: str) -> bool:
        """
        Click a menu option - intelligently left-clicks default or opens menu.

        This method is smart:
        - If the option is the default (first on menu), it left-clicks directly
        - Otherwise, it opens the menu (right-click) and clicks the option

        Args:
            option_text: Text to search for in menu options (e.g., "Drop", "Eat")
            button: Mouse button for menu selection ('left' or 'right')
            duration: Time to take moving to the option (seconds)

        Returns:
            True if option was found and clicked, False otherwise

        Example:
            # Smart: left-clicks if "Eat" is default, otherwise opens menu
            menu.clickOption("Eat")

            # Click "Drop" option (will open menu if not default)
            menu.clickOption("Drop")
        """
        if self.isOpen():
            self.hoverOption(option_text)
            self.client.input.mouse.leftClick()
            return self.waitOptionClicked(option_text)
        
        left_click_option = self.getLeftClickOption()
        if left_click_option is None:
            return False
        
        if option_text.lower() in left_click_option.lower():
            # It's the default! Just left-click at current position
            self.client.input.mouse.leftClick()
            return self.waitOptionClicked(option_text)
        
        options = self.getOptions()

        if not self.hasOption(option_text):
            return False
        
        self.open()
        self.hoverOption(option_text)
        self.client.input.mouse.leftClick()
        return self.waitOptionClicked(option_text)

    def clickOptionIndex(self, option_index: int) -> bool:
        """
        Click a menu option by its index.

        Automatically opens menu if not already open.

        Args:
            option_index: Index of the option (0 = first/top option)

        Returns:
            True if option was clicked, False if invalid index

        Example:
            # Click the first menu option
            menu.clickOptionIndex(0)

            # Right-click the second option
            menu.clickOptionIndex(1
        """
        # Ensure menu is open
        if not self.open():
            return False

        box = self.getOptionBox(option_index)
        if box:
            box.click()
            return True
        return False

    def clickOptionType(self, option_type: str) -> bool:
        """
        Click a menu option by its type.

        Automatically opens menu if not already open.

        Args:
            option_type: Type of the option, see https://static.runelite.net/runelite-api/apidocs/net/runelite/api/MenuAction.html

        Returns:
            True if option was clicked, False otherwise

        Example:
            # Click the "Use" option on any item
            menu.clickOptionType("WIDGET_TARGET")
        """
        options, types = self._getOptions(strip_colors=True)
        for i, t in enumerate(types):
            if option_type.lower() in t.lower():
                return self.clickOption(options[i])
        return False
