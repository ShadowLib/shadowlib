"""Circle geometry type."""

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shadowlib.types.point import Point


@dataclass
class Circle:
    """
    Represents a circle with integer center coordinates and float radius.

    Attributes:
        centerX: X coordinate of center
        centerY: Y coordinate of center
        radius: Radius of the circle

    Example:
        >>> circle = Circle(100, 100, 50)
        >>> circle.click()  # Click at random point within circle
        >>> if circle.contains(Point(120, 110)):
        ...     print("Point is inside circle")
    """

    centerX: int
    centerY: int
    radius: float

    def center(self) -> "Point":
        """
        Get the center point of the circle.

        Returns:
            Point at the center

        Example:
            >>> circle = Circle(100, 100, 50)
            >>> center = circle.center()  # Point(100, 100)
        """
        from shadowlib.types.point import Point

        return Point(self.centerX, self.centerY)

    def area(self) -> float:
        """
        Get the area of the circle.

        Returns:
            Area in square pixels

        Example:
            >>> circle = Circle(100, 100, 10)
            >>> circle.area()  # Returns approximately 314.159
        """
        return math.pi * self.radius * self.radius

    def contains(self, point: "Point") -> bool:
        """
        Check if a point is within this circle.

        Args:
            point: Point to check

        Returns:
            True if point is inside circle, False otherwise

        Example:
            >>> circle = Circle(100, 100, 50)
            >>> circle.contains(Point(120, 110))  # True
            >>> circle.contains(Point(200, 200))  # False
        """
        dx = point.x - self.centerX
        dy = point.y - self.centerY
        return math.sqrt(dx * dx + dy * dy) <= self.radius

    def randomPoint(self) -> "Point":
        """
        Generate a uniformly random point within this circle.

        Uses the polar method with sqrt for true uniform distribution.

        Returns:
            Random Point inside the circle

        Example:
            >>> circle = Circle(100, 100, 50)
            >>> point = circle.randomPoint()
        """
        from shadowlib.types.point import Point

        # Use sqrt to get uniform distribution (not just random angle/radius)
        r = self.radius * math.sqrt(random.random())
        theta = random.uniform(0, 2 * math.pi)

        x = self.centerX + int(r * math.cos(theta))
        y = self.centerY + int(r * math.sin(theta))

        return Point(x, y)

    def click(self, button: str = "left", randomize: bool = True) -> None:
        """
        Click within this circle.

        Args:
            button: Mouse button ('left', 'right')
            randomize: If True, clicks at random point. If False, clicks at center.

        Example:
            >>> circle = Circle(100, 100, 50)
            >>> circle.click()  # Random click inside circle
            >>> circle.click(randomize=False)  # Click at center
        """
        point = self.randomPoint() if randomize else self.center()
        point.click(button=button)

    def hover(self, randomize: bool = True) -> None:
        """
        Move mouse to hover within this circle.

        Args:
            randomize: If True, hovers at random point. If False, hovers at center.

        Example:
            >>> circle = Circle(100, 100, 50)
            >>> circle.hover()  # Hover at random point
        """
        point = self.randomPoint() if randomize else self.center()
        point.hover()

    def rightClick(self, randomize: bool = True) -> None:
        """
        Right-click within this circle.

        Args:
            randomize: If True, clicks at random point. If False, clicks at center.

        Example:
            >>> circle = Circle(100, 100, 50)
            >>> circle.rightClick()
        """
        self.click(button="right", randomize=randomize)

    def __repr__(self) -> str:
        return f"Circle(center=({self.centerX}, {self.centerY}), radius={self.radius})"

    def debug(self, color: tuple[int, int, int] | str = "red", width: int = 2) -> None:
        """
        Visualize this circle on a fresh capture of the game window.

        Args:
            color: Outline color (RGB tuple or name)
            width: Line width in pixels

        Example:
            >>> circle = Circle(150, 150, 50)
            >>> circle.debug()  # Shows circle on game screenshot
        """
        from shadowlib._internal.visualizer import Visualizer

        viz = Visualizer()
        if viz.capture():
            viz.drawCircle(self, color=color, width=width)
            viz.render()
