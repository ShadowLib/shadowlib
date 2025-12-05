"""Point geometry types for 2D and 3D coordinates."""

import math
from dataclasses import dataclass


@dataclass
class Point:
    """
    Represents a 2D point with integer coordinates.

    Attributes:
        x: X coordinate
        y: Y coordinate

    Example:
        >>> point = Point(100, 200)
        >>> point.click()  # Click at this point
        >>> distance = point.distanceTo(Point(150, 250))
    """

    x: int
    y: int

    def distanceTo(self, other: "Point") -> float:
        """
        Calculate Euclidean distance to another point.

        Args:
            other: Another Point instance

        Returns:
            Distance as a float

        Example:
            >>> p1 = Point(0, 0)
            >>> p2 = Point(3, 4)
            >>> p1.distanceTo(p2)  # Returns 5.0
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def click(self, button: str = "left") -> None:
        """
        Click at this point.

        Args:
            button: Mouse button ('left', 'right')

        Example:
            >>> point = Point(100, 200)
            >>> point.click()  # Left click
            >>> point.click(button="right")  # Right click
        """
        from shadowlib.globals import getClient

        mouse = getClient().input.mouse
        if button == "left":
            mouse.leftClick(self.x, self.y)
        else:
            mouse.rightClick(self.x, self.y)

    def hover(self) -> None:
        """
        Move mouse to hover over this point.

        Example:
            >>> point = Point(100, 200)
            >>> point.hover()
        """
        from shadowlib.globals import getClient

        mouse = getClient().input.mouse
        mouse.moveTo(self.x, self.y)

    def rightClick(self) -> None:
        """
        Right-click at this point.

        Example:
            >>> point = Point(100, 200)
            >>> point.rightClick()
        """
        self.click(button="right")

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"

    def debug(self, color: tuple[int, int, int] | str = "red", size: int = 5) -> None:
        """
        Visualize this point on a fresh capture of the game window.

        Args:
            color: Color (RGB tuple or name)
            size: Size of the crosshair in pixels

        Example:
            >>> point = Point(150, 150)
            >>> point.debug()  # Shows crosshair on game screenshot
        """
        from shadowlib._internal.visualizer import Visualizer

        viz = Visualizer()
        if viz.capture():
            viz.drawPoint(self, color=color, size=size)
            viz.render()


@dataclass
class Point3D:
    """
    Represents a 3D point with integer coordinates.

    Attributes:
        x: X coordinate
        y: Y coordinate
        z: Z coordinate

    Example:
        >>> point = Point3D(100, 200, 0)
        >>> distance = point.distanceTo(Point3D(150, 250, 5))
        >>> point2d = point.to2d()  # Convert to 2D Point
    """

    x: int
    y: int
    z: int

    def distanceTo(self, other: "Point3D") -> float:
        """
        Calculate 3D Euclidean distance to another point.

        Args:
            other: Another Point3D instance

        Returns:
            Distance as a float

        Example:
            >>> p1 = Point3D(0, 0, 0)
            >>> p2 = Point3D(3, 4, 0)
            >>> p1.distanceTo(p2)  # Returns 5.0
        """
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def to2d(self) -> Point:
        """
        Convert to 2D point (dropping z coordinate).

        Returns:
            A Point instance with x and y coordinates

        Example:
            >>> point3d = Point3D(100, 200, 50)
            >>> point2d = point3d.to2d()  # Point(100, 200)
        """
        return Point(self.x, self.y)

    def __repr__(self) -> str:
        return f"Point3D({self.x}, {self.y}, {self.z})"
