"""Box (rectangular area) geometry type."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shadowlib.types.point import Point


@dataclass
class Box:
    """
    Represents a rectangular area (axis-aligned box) with integer coordinates.

    Attributes:
        x1: Left edge x-coordinate
        y1: Top edge y-coordinate
        x2: Right edge x-coordinate
        y2: Bottom edge y-coordinate

    Example:
        >>> box = Box(100, 100, 200, 200)
        >>> box.click()  # Click at random point within box
        >>> box.click(randomize=False)  # Click at center
        >>> if box.contains(Point(150, 150)):
        ...     print("Point is inside box")
    """

    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self):
        """Ensure coordinates are ordered correctly (x1 < x2, y1 < y2)."""
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
        if self.y1 > self.y2:
            self.y1, self.y2 = self.y2, self.y1

    @classmethod
    def fromRect(cls, x: int, y: int, width: int, height: int) -> "Box":
        """
        Create a Box from Java Rectangle format (x, y, width, height).

        Args:
            x: Left edge x-coordinate
            y: Top edge y-coordinate
            width: Width in pixels
            height: Height in pixels

        Returns:
            New Box instance

        Example:
            >>> box = Box.fromRect(100, 100, 50, 50)  # Same as Box(100, 100, 150, 150)
        """
        return cls(x, y, x + width, y + height)

    def width(self) -> int:
        """
        Get width of the box.

        Returns:
            Width in pixels

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.width()  # Returns 100
        """
        return self.x2 - self.x1

    def height(self) -> int:
        """
        Get height of the box.

        Returns:
            Height in pixels

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.height()  # Returns 100
        """
        return self.y2 - self.y1

    def area(self) -> int:
        """
        Get area of the box.

        Returns:
            Area in square pixels

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.area()  # Returns 10000
        """
        return self.width() * self.height()

    def center(self) -> "Point":
        """
        Get the center point of the box.

        Returns:
            Point at the center

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> center = box.center()  # Point(150, 150)
        """
        from shadowlib.types.point import Point

        return Point((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def contains(self, other: "Point | Box") -> bool:
        """
        Check if a point or box is within this box.

        Args:
            other: Point or Box to check

        Returns:
            True if other is inside this box, False otherwise

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.contains(Point(150, 150))  # True
            >>> box.contains(Box(120, 120, 180, 180))  # True
        """
        if isinstance(other, Box):
            return (
                self.x1 <= other.x1
                and other.x2 <= self.x2
                and self.y1 <= other.y1
                and other.y2 <= self.y2
            )
        return self.x1 <= other.x < self.x2 and self.y1 <= other.y < self.y2

    def randomPoint(self) -> "Point":
        """
        Generate a random point within this box.

        Returns:
            Random Point inside the box

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> point = box.randomPoint()  # Random point between (100,100) and (199,199)
        """
        from shadowlib.types.point import Point

        return Point(random.randrange(self.x1, self.x2), random.randrange(self.y1, self.y2))

    def click(self, button: str = "left", randomize: bool = True) -> None:
        """
        Click within this box.

        Args:
            button: Mouse button ('left', 'right')
            randomize: If True, clicks at random point. If False, clicks at center.

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.click()  # Random click inside box
            >>> box.click(randomize=False)  # Click at center
            >>> box.click(button="right")  # Right-click at random point
        """
        point = self.randomPoint() if randomize else self.center()
        point.click(button=button)

    def hover(self, randomize: bool = True) -> None:
        """
        Move mouse to hover within this box.

        Args:
            randomize: If True, hovers at random point. If False, hovers at center.

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.hover()  # Hover at random point
            >>> box.hover(randomize=False)  # Hover at center
        """
        point = self.randomPoint() if randomize else self.center()
        point.hover()

    def rightClick(self, randomize: bool = True) -> None:
        """
        Right-click within this box.

        Args:
            randomize: If True, clicks at random point. If False, clicks at center.

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.rightClick()
        """
        self.click(button="right", randomize=randomize)

    def clickOption(self, option: str, randomize: bool = True) -> bool:
        """
        Click a specific option from the context menu after right-clicking within this box.

        Args:
            option: Menu option to click
            randomize: If True, right-clicks at random point. If False, right-clicks at center.
        Returns:
            True if option was clicked, False otherwise.
        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.clickOption("Examine")
        """
        from shadowlib.client import client

        self.hover(randomize=randomize)
        if client.interactions.menu.waitHasOption(option):
            return client.interactions.menu.clickOption(option)
        return False

    def __repr__(self) -> str:
        return f"Box({self.x1}, {self.y1}, {self.x2}, {self.y2})"

    def debug(self, color: tuple[int, int, int] | str = "red", width: int = 2) -> None:
        """
        Visualize this box on a fresh capture of the game window.

        Args:
            color: Outline color (RGB tuple or name)
            width: Line width in pixels

        Example:
            >>> box = Box(100, 100, 200, 200)
            >>> box.debug()  # Shows box on game screenshot
        """
        from shadowlib._internal.visualizer import Visualizer

        viz = Visualizer()
        if viz.capture():
            viz.drawBox(self, color=color, width=width)
            viz.render()


def createGrid(
    startX: int,
    startY: int,
    width: int,
    height: int,
    columns: int,
    rows: int,
    spacingX: int = 0,
    spacingY: int = 0,
    padding: int = 0,
) -> list[Box]:
    """
    Create a grid of Box objects.

    Args:
        startX: X coordinate of the top-left corner of the first box
        startY: Y coordinate of the top-left corner of the first box
        width: Width of each box in pixels
        height: Height of each box in pixels
        columns: Number of columns in the grid
        rows: Number of rows in the grid
        spacingX: Horizontal spacing between boxes (default: 0)
        spacingY: Vertical spacing between boxes (default: 0)
        padding: Inner padding for each box in pixels (shrinks box on all sides, default: 0)

    Returns:
        List of Box objects in row-major order (left to right, top to bottom)

    Example:
        >>> # Create a 4x7 inventory grid
        >>> slots = createGrid(563, 213, 36, 32, columns=4, rows=7, spacingX=6, spacingY=4)
        >>> # slots[0] is top-left, slots[3] is top-right, slots[4] is second row left, etc.
        >>>
        >>> # Create grid with 2px padding to avoid edge clicks
        >>> slots = createGrid(563, 213, 36, 32, columns=4, rows=7, spacingX=6, spacingY=4, padding=2)
    """
    boxes = []
    for row in range(rows):
        for col in range(columns):
            x1 = startX + col * (width + spacingX)
            y1 = startY + row * (height + spacingY)
            x2 = x1 + width
            y2 = y1 + height

            # Apply padding (shrink box on all sides)
            if padding > 0:
                x1 += padding
                y1 += padding
                x2 -= padding
                y2 -= padding

            boxes.append(Box(x1, y1, x2, y2))
    return boxes
