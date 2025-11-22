"""
Menu module - handles right-click context menu interactions.
"""

import re
import time
from typing import List, Optional, Tuple

from shadowlib.globals import getClient

from ..utils.geometry import Area


def _stripColorTags(text: str) -> str:
    """
    Remove RuneScape color and image tags from text.

    Tags include:
    - Color tags: <col=RRGGBB> and </col>
    - Image tags: <img=NUMBER>
    - Any other tags in angle brackets

    Args:
        text: Text with potential tags

    Returns:
        Text with all tags removed

    Example:
        >>> _stripColorTags("Follow <col=ffffff>Player</col>  (level-99)")
        "Follow Player  (level-99)"
        >>> _stripColorTags("<img=54> Drop Logs")
        " Drop Logs"
        >>> _stripColorTags("Cast Confuse</col>")
        "Cast Confuse"
    """
    # Remove all tags in angle brackets (opening and closing)
    text = re.sub(r"<[^>]+>", "", text)
    return text


class Menu:
    """
    Menu operations class for handling right-click context menus.
    """

    def __init__(self, client=None):
        """
        Initialize menu manager.

        Args:
            client: Optional Client instance. If None, uses global Client.
        """
        self.client = client or getClient()

    def waitUntilOpen(self, timeout: float = 1.0, poll_interval: float = 0.005) -> bool:
        """
        Wait until the menu is open, polling every 5ms (frame-level).

        Args:
            timeout: Maximum time to wait in seconds
            poll_interval: Time between checks in seconds (default: 5ms)

        Returns:
            True if menu opened within timeout, False otherwise
        """
        # TODO: Update when new cache system is implemented
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            # Check if menu is open
            if self.isOpen():
                return True
            time.sleep(poll_interval)

        return False

    def open(self, timeout: float = 1.0) -> bool:
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
        from ..io.io import IO

        # Right-click at current position
        io = IO()
        io.mouse.click(button="right")

        # Wait for menu to open
        return self.waitUntilOpen(timeout=timeout)

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

        from ..io.io import IO

        # Check if menu is open
        if not self.client.cache.get("isOpen", False):
            return True  # Already closed

        # Get menu state from cache
        scrollable = self.client.cache.get("scrollable", False)
        menu_x = self.client.cache.get("menuX", 0)
        menu_y = self.client.cache.get("menuY", 0)
        menu_width = self.client.cache.get("width", 0)
        menu_height = self.client.cache.get("height", 0)

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
                area = self.getOptionArea(cancel_index)
                if area:
                    area.click()
            else:
                # Cancel not found, fall back to mouse move
                use_cancel = False

        if not use_cancel:
            # Move mouse at least 30 pixels away from menu area
            menu_x1 = menu_x
            menu_y1 = menu_y
            menu_x2 = menu_x + menu_width
            menu_y2 = menu_y + menu_height

            # Pick a random direction and move 30-50 pixels away
            io = IO()
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
            io.mouse.move(target_x, target_y, duration=0.1)

        # Wait for menu to close
        # TODO: Update when new cache system is implemented
        start_time = time.time()
        poll_interval = 0.005
        while (time.time() - start_time) < timeout:
            if not self.isOpen():
                return True
            time.sleep(poll_interval)

        return False

    def isOpen(self) -> bool:
        """
        Check if the right-click context menu is currently open.

        Reads from game state cache (updated every tick).

        Returns:
            True if menu is open, False otherwise
        """
        return self.client.cache.get("isOpen", False)

    def getPosition(self) -> Tuple[int, int]:
        """
        Get the menu's top-left position.

        Reads from game state cache (updated every tick).

        Returns:
            Tuple of (x, y) coordinates
        """
        return (self.client.cache.get("menuX", 0), self.client.cache.get("menuY", 0))

    def getDimensions(self) -> Tuple[int, int]:
        """
        Get the menu's width and height.

        Reads from game state cache (updated every tick).

        Returns:
            Tuple of (width, height) in pixels
        """
        return (self.client.cache.get("width", 0), self.client.cache.get("height", 0))

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
        menu_options = self.client.cache.get("menu_options", [])

        if not menu_options:
            return []

        # Combine [option, target] pairs with a space
        formatted_options = [f"{option} {target}".strip() for option, target in menu_options]

        # Strip color tags if requested
        if strip_colors:
            formatted_options = [_stripColorTags(opt) for opt in formatted_options]

        # Reverse because they're stored backwards (last item is first option)
        formatted_options.reverse()

        return formatted_options

    def getDefaultOption(self, strip_colors: bool = True) -> Optional[str]:
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
        menu_options = self.client.cache.get("menu_options", [])

        if not menu_options:
            return None

        # Last item in array = first option on menu = default action
        option, target = menu_options[-1]
        formatted = f"{option} {target}".strip()

        if strip_colors:
            formatted = _stripColorTags(formatted)

        return formatted

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

        for option in options:
            if option_text_lower in option.lower():
                return True

        return False

    def getOptionArea(self, option_index: int) -> Optional[Area]:
        """
        Get the clickable area for a specific menu option.

        Menu option areas are calculated based on:
        - Menu position (menuX, menuY)
        - Offset: (2, 19) from menu position to first option
        - Each option: (menuWidth - 4) wide, 15 pixels total height
        - Options stack vertically with no overlap

        Args:
            option_index: Index of the option (0 = first/top option)

        Returns:
            Area object for the option, or None if invalid index

        Example:
            area = menu.getOptionArea(0)  # Get first option's area
            if area:
                area.click()
        """
        if not self.isOpen():
            return None

        options = self.getOptions()
        if not options or option_index < 0 or option_index >= len(options):
            return None

        menu_x, menu_y = self.getPosition()
        menu_width, _ = self.getDimensions()

        # First option starts at offset (2, 19) from menu position
        option_x1 = menu_x + 2
        option_y1 = menu_y + 19 + (option_index * 15)

        # Each option is (menuWidth - 4) wide and spans 15 pixels
        # Using x2 = x1 + width - 1 to avoid overlap (e.g., 100-114 = 15 pixels)
        option_x2 = option_x1 + (menu_width - 4) - 1
        option_y2 = option_y1 + 14  # 15 pixels total: y1 to y1+14 inclusive

        return Area(option_x1, option_y1, option_x2, option_y2)

    def hoverOption(self, option_text: str, duration: float = 0.2) -> bool:
        """
        Hover over a menu option by matching text.

        Automatically opens menu if not already open.

        Args:
            option_text: Text to search for in menu options (e.g., "Drop", "Use")
            duration: Time to take moving to the option (seconds)

        Returns:
            True if option was found and hovered, False otherwise
        """
        # Ensure menu is open
        if not self.client.cache.get("isOpen", False):
            if not self.open():
                return False

        options = self.getOptions()
        option_text_lower = option_text.lower()

        for i, option in enumerate(options):
            if option_text_lower in option.lower():
                area = self.getOptionArea(i)
                if area:
                    area.hover(duration=duration)
                    return True

        return False

    def hoverOptionIndex(self, option_index: int, duration: float = 0.2) -> bool:
        """
        Hover over a menu option by its index.

        Automatically opens menu if not already open.

        Args:
            option_index: Index of the option (0 = first/top option)
            duration: Time to take moving to the option (seconds)

        Returns:
            True if option was hovered, False if invalid index

        Example:
            # Hover over the first menu option (opens menu if needed)
            menu.hoverOptionIndex(0)
        """
        # Ensure menu is open
        if not self.client.cache.get("isOpen", False):
            if not self.open():
                return False

        area = self.getOptionArea(option_index)
        if area:
            area.hover(duration=duration)
            return True
        return False

    def clickOption(self, option_text: str, button: str = "left", duration: float = 0.2) -> bool:
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
        from ..io.io import IO

        # TODO: Update when new cache system is implemented
        # Get menu options from cache
        menu_options = self.client.cache.get("menu_options", [])
        option_text_lower = option_text.lower()

        # Check if it's the default option (can left-click directly without opening menu)
        if menu_options:
            # Last item in array = first on menu = default action
            default_option, default_target = menu_options[-1]
            default_formatted = f"{default_option} {default_target}".strip()
            default_formatted = _stripColorTags(default_formatted)

            if option_text_lower in default_formatted.lower():
                # It's the default! Just left-click at current position
                io = IO()
                io.mouse.click(button="left")
                return True

        # Not default - need to open menu
        if not self.client.cache.get("isOpen", False):
            if not self.open():
                return False

        # Find and click the option
        options = self.getOptions()

        for i, option in enumerate(options):
            if option_text_lower in option.lower():
                area = self.getOptionArea(i)
                if area:
                    area.click(button=button, duration=duration)
                    return True

        return False

    def clickOptionIndex(
        self, option_index: int, button: str = "left", duration: float = 0.2
    ) -> bool:
        """
        Click a menu option by its index.

        Automatically opens menu if not already open.

        Args:
            option_index: Index of the option (0 = first/top option)
            button: Mouse button ('left', 'right', 'middle')
            duration: Time to take moving to the option (seconds)

        Returns:
            True if option was clicked, False if invalid index

        Example:
            # Click the first menu option
            menu.clickOptionIndex(0)

            # Right-click the second option
            menu.clickOptionIndex(1, button='right')
        """
        # Ensure menu is open
        if not self.client.cache.get("isOpen", False):
            if not self.open():
                return False

        area = self.getOptionArea(option_index)
        if area:
            area.click(button=button, duration=duration)
            return True
        return False


# Module-level default instance
_default = Menu()

# Export methods
isOpen = _default.is_open
getPosition = _default.get_position
getDimensions = _default.get_dimensions
getOptions = _default.get_options
getDefaultOption = _default.get_default_option
hasOption = _default.has_option
getOptionArea = _default.get_option_area
open = _default.open
close = _default.close
waitUntilOpen = _default.wait_until_open
hoverOption = _default.hover_option
hoverOptionIndex = _default.hover_option_index
clickOption = _default.click_option
clickOptionIndex = _default.click_option_index
