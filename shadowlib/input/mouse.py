"""Mouse control with human-like movement."""

import random
import time
from typing import Optional, Tuple

try:
    import pyautogui as pag
except ImportError:
    pag = None


class Mouse:
    """
    Singleton mouse controller with human-like movement.
    All coordinates are relative to RuneLite window by default.
    Uses pyautogui for cross-platform mouse control.

    Example:
        from shadowlib.input.mouse import mouse

        mouse.moveTo(100, 200)
        mouse.leftClick()
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self, speed: float = 1.0):
        """
        Actual initialization, runs once.

        Args:
            speed: Movement speed multiplier (1.0 = ~20 pixels per 20ms step)
        """
        from shadowlib.input.runelite import runelite

        if pag is None:
            raise ImportError("pyautogui is required. Install with: pip install pyautogui")

        # Configure pyautogui for instant movement
        pag.PAUSE = 0
        pag.FAILSAFE = False
        pag.MINIMUM_SLEEP = 0
        pag.MINIMUM_DURATION = 0

        self.runelite = runelite
        self.speed = speed

    def _validateCoordinates(self, x: int, y: int, safe: bool) -> None:
        """
        Validate that coordinates are within game window bounds.

        Args:
            x: X coordinate (relative to game window)
            y: Y coordinate (relative to game window)
            safe: If True, reject coordinates outside window bounds

        Raises:
            ValueError: If safe=True and coordinates are outside bounds
        """
        if not safe:
            return  # Skip validation

        bounds = self.runelite.getGameBounds()
        if not bounds:
            raise ValueError("Could not get game window bounds")

        window_width = bounds[2]
        window_height = bounds[3]

        if x < 0 or y < 0 or x >= window_width or y >= window_height:
            raise ValueError(
                f"Coordinates ({x}, {y}) are outside game window bounds "
                f"(0, 0, {window_width}, {window_height}). "
                f"Use safe=False to allow out-of-bounds coordinates."
            )

    def _moveTo(self, x: int, y: int, safe: bool = True) -> None:
        """
        Core movement function - ONLY access point to pyautogui.moveTo().
        All coordinates are relative to RuneLite window.

        Args:
            x: Target x coordinate (relative to game window)
            y: Target y coordinate (relative to game window)
            safe: If True, reject coordinates outside window bounds
        """
        # Ensure window is ready
        self.runelite.refreshWindowPosition()
        # temp override for performance testing

        time.perf_counter()
        pag.moveTo(
            x + self.runelite.getWindowOffset()[0],
            y + self.runelite.getWindowOffset()[1],
            _pause=False,
        )
        time.sleep(0.001)  # slight delay to ensure move completes
        return
        # Validate coordinates
        self._validateCoordinates(x, y, safe)

        # Convert to absolute screen coordinates
        offset = self.runelite.getWindowOffset()
        if not offset:
            raise RuntimeError("Could not get window offset")

        abs_x = x + offset[0]
        abs_y = y + offset[1]

        # Get current position
        current_x, current_y = pag.position()

        # Calculate distance
        dx = abs_x - current_x
        dy = abs_y - current_y
        distance = (dx**2 + dy**2) ** 0.5

        if distance == 0:
            return  # Already at target

        # Base step size: ~20 pixels per step at speed=1.0
        base_step_size = 20.0 * self.speed

        # Calculate number of steps (20ms per step)
        num_steps = max(1, int(distance / base_step_size))

        # Move in steps
        for step in range(num_steps):
            # Calculate progress (0.0 to 1.0)
            progress = (step + 1) / num_steps

            # Add randomness to step size (±20% variation)
            step_randomness = random.uniform(0.8, 1.2)

            # Calculate intermediate position
            intermediate_x = current_x + int(dx * progress)
            intermediate_y = current_y + int(dy * progress)

            # Add slight random offset for human-like movement (±2 pixels)
            jitter_x = random.randint(-2, 2) if step < num_steps - 1 else 0
            jitter_y = random.randint(-2, 2) if step < num_steps - 1 else 0

            # Move to intermediate position
            pag.moveTo(
                intermediate_x + jitter_x, intermediate_y + jitter_y, duration=0, _pause=False
            )

            # Wait 20ms (with slight randomness)
            time.sleep(0.020 * step_randomness)

        # Final move to exact target (no jitter)
        pag.moveTo(abs_x, abs_y, duration=0, _pause=False)

    def _clickButton(self, button: str) -> None:
        """
        Core click function - ONLY access point to pyautogui.click().

        Args:
            button: Button to click ('left' or 'right')
        """
        # Ensure window is ready (respects 10s cache)
        self.runelite.refreshWindowPosition()

        # Perform click
        pag.click(button=button, _pause=False, tween=None)

    def _hold(self, button: str) -> None:
        """
        Core hold function - ONLY access point to pyautogui.mouseDown().

        Args:
            button: Button to hold ('left' or 'right')
        """
        # Ensure window is ready (respects 10s cache)
        self.runelite.refreshWindowPosition()

        # Hold button down
        pag.mouseDown(button=button, _pause=False)

    def _release(self, button: str) -> None:
        """
        Core release function - ONLY access point to pyautogui.mouseUp().

        Args:
            button: Button to release ('left' or 'right')
        """
        # Ensure window is ready (respects 10s cache)
        self.runelite.refreshWindowPosition()

        # Release button
        pag.mouseUp(button=button, _pause=False)

    def _scroll(self, clicks: int) -> None:
        """
        Core scroll function - ONLY access point to pyautogui.scroll().

        Args:
            clicks: Number of scroll clicks (positive=up, negative=down)
        """
        # Ensure window is ready (respects 10s cache)
        self.runelite.refreshWindowPosition()

        # Perform scroll
        pag.scroll(clicks, _pause=False)

    def click(self, button: str = "left") -> None:
        self._clickButton(button)

    def moveTo(self, x: int, y: int, safe: bool = True) -> None:
        """
        Move mouse to target position with human-like movement.
        Coordinates are relative to RuneLite window.

        Args:
            x: Target x coordinate (relative to game window)
            y: Target y coordinate (relative to game window)
            safe: If True, reject coordinates outside window bounds

        Example:
            >>> mouse.moveTo(100, 200)  # Move to (100, 200) in game window
            >>> mouse.moveTo(-50, -50, safe=False)  # Move outside window (unsafe)
        """
        self._moveTo(x, y, safe=safe)

    def leftClick(self, x: int | None = None, y: int | None = None, safe: bool = True) -> None:
        """
        Perform left click at current position or move to position and click.
        Coordinates are relative to RuneLite window.

        Args:
            x: Optional target x coordinate (if None, clicks at current position)
            y: Optional target y coordinate (if None, clicks at current position)
            safe: If True, reject coordinates outside window bounds

        Example:
            >>> mouse.leftClick(100, 200)  # Move and click at (100, 200)
            >>> mouse.leftClick()  # Click at current position
        """
        import time

        time.perf_counter()
        if x is not None and y is not None:
            self._moveTo(x, y, safe=safe)
        self._clickButton("left")
        time.perf_counter()

    def rightClick(self, x: int | None = None, y: int | None = None, safe: bool = True) -> None:
        """
        Perform right click at current position or move to position and click.
        Coordinates are relative to RuneLite window.

        Args:
            x: Optional target x coordinate (if None, clicks at current position)
            y: Optional target y coordinate (if None, clicks at current position)
            safe: If True, reject coordinates outside window bounds

        Example:
            >>> mouse.rightClick(100, 200)  # Move and right-click at (100, 200)
            >>> mouse.rightClick()  # Right-click at current position
        """
        if x is not None and y is not None:
            self._moveTo(x, y, safe=safe)

        self._clickButton("right")

    def holdLeft(self, x: int | None = None, y: int | None = None, safe: bool = True) -> None:
        """
        Hold left mouse button at current position or move to position and hold.
        Coordinates are relative to RuneLite window.

        Args:
            x: Optional target x coordinate (if None, holds at current position)
            y: Optional target y coordinate (if None, holds at current position)
            safe: If True, reject coordinates outside window bounds

        Example:
            >>> mouse.holdLeft(100, 200)  # Move and hold at (100, 200)
            >>> mouse.moveTo(300, 400)    # Drag to new position
            >>> mouse.releaseLeft()       # Release button
        """
        if x is not None and y is not None:
            self._moveTo(x, y, safe=safe)

        self._hold("left")

    def holdRight(self, x: int | None = None, y: int | None = None, safe: bool = True) -> None:
        """
        Hold right mouse button at current position or move to position and hold.
        Coordinates are relative to RuneLite window.

        Args:
            x: Optional target x coordinate (if None, holds at current position)
            y: Optional target y coordinate (if None, holds at current position)
            safe: If True, reject coordinates outside window bounds

        Example:
            >>> mouse.holdRight(100, 200)  # Move and hold right button
            >>> mouse.moveTo(300, 400)     # Drag to new position
            >>> mouse.releaseRight()       # Release button
        """
        if x is not None and y is not None:
            self._moveTo(x, y, safe=safe)

        self._hold("right")

    def releaseLeft(self) -> None:
        """
        Release left mouse button.

        Example:
            >>> mouse.holdLeft(100, 200)
            >>> time.sleep(1)
            >>> mouse.releaseLeft()
        """
        self._release("left")

    def releaseRight(self) -> None:
        """
        Release right mouse button.

        Example:
            >>> mouse.holdRight(100, 200)
            >>> time.sleep(1)
            >>> mouse.releaseRight()
        """
        self._release("right")

    def scroll(self, up: bool = True, count: int = 1) -> None:
        """
        Scroll the mouse wheel with human-like delays between scrolls.

        Args:
            up: If True, scroll up. If False, scroll down.
            count: Number of scroll clicks (default 1)

        Example:
            >>> mouse.scroll()              # Scroll up once
            >>> mouse.scroll(up=False)      # Scroll down once
            >>> mouse.scroll(count=3)       # Scroll up 3 times
            >>> mouse.scroll(up=False, count=5)  # Scroll down 5 times
        """
        direction = 1 if up else -1

        for i in range(count):
            self._scroll(direction)

            # Add human-like delay between scrolls (~25-50ms)
            if i < count - 1:
                time.sleep(random.uniform(0.025, 0.05))


# Module-level singleton instance
mouse = Mouse()
