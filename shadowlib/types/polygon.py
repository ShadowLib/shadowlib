"""Polygon geometry type."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from shadowlib.types.point import Point


@dataclass
class Polygon:
    """
    Represents an arbitrary polygon defined by n vertices.

    Attributes:
        vertices: List of Point objects defining the polygon vertices

    Example:
        >>> from shadowlib.types.point import Point
        >>> polygon = Polygon([Point(100, 100), Point(200, 100), Point(150, 200)])
        >>> polygon.click()  # Click at random point within polygon
        >>> if polygon.contains(Point(150, 150)):
        ...     print("Point is inside polygon")
    """

    vertices: List["Point"]

    def __post_init__(self):
        """Validate polygon has at least 3 vertices."""
        if len(self.vertices) < 3:
            raise ValueError("Polygon must have at least 3 vertices")

    def fromArray(self, data: List[List[int]]) -> None:
        """
        Populate Polygon from array of [x, y] coordinate pairs.

        Args:
            data: List of [x, y] pairs

        Example:
            >>> polygon = Polygon([])
            >>> polygon.fromArray([[0, 0], [100, 0], [50, 100]])
        """
        from shadowlib.types.point import Point

        x_data = data[0]
        y_data = data[1]

        self.vertices = [Point(x, y) for x, y in zip(x_data, y_data)]

    def center(self) -> "Point":
        """
        Get the centroid (center of mass) of the polygon.

        Returns:
            Point at the centroid

        Example:
            >>> polygon = Polygon([Point(0, 0), Point(100, 0), Point(50, 100)])
            >>> center = polygon.center()
        """
        from shadowlib.types.point import Point

        x_sum = sum(v.x for v in self.vertices)
        y_sum = sum(v.y for v in self.vertices)
        n = len(self.vertices)
        return Point(x_sum // n, y_sum // n)

    def bounds(self) -> tuple[int, int, int, int]:
        """
        Get the bounding box of this polygon.

        Returns:
            Tuple of (minX, minY, maxX, maxY)

        Example:
            >>> polygon = Polygon([Point(0, 0), Point(100, 0), Point(50, 100)])
            >>> bounds = polygon.bounds()  # (0, 0, 100, 100)
        """
        min_x = min(v.x for v in self.vertices)
        min_y = min(v.y for v in self.vertices)
        max_x = max(v.x for v in self.vertices)
        max_y = max(v.y for v in self.vertices)
        return (min_x, min_y, max_x, max_y)

    def contains(self, point: "Point") -> bool:
        """
        Check if a point is within this polygon using ray casting algorithm.

        Args:
            point: Point to check

        Returns:
            True if point is inside polygon, False otherwise

        Example:
            >>> polygon = Polygon([Point(0, 0), Point(100, 0), Point(50, 100)])
            >>> polygon.contains(Point(50, 50))  # True
            >>> polygon.contains(Point(200, 200))  # False
        """
        x, y = point.x, point.y
        n = len(self.vertices)
        inside = False

        p1x, p1y = self.vertices[0].x, self.vertices[0].y
        for i in range(1, n + 1):
            p2x, p2y = self.vertices[i % n].x, self.vertices[i % n].y
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def area(self) -> float:
        """
        Calculate the area of the polygon using the shoelace formula.

        Returns:
            Area in square pixels

        Example:
            >>> polygon = Polygon([Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)])
            >>> polygon.area()  # Returns 10000.0
        """
        n = len(self.vertices)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.vertices[i].x * self.vertices[j].y
            area -= self.vertices[j].x * self.vertices[i].y
        return abs(area) / 2.0

    def randomPoint(self) -> "Point":
        """
        Generate a random point within this polygon using rejection sampling.

        Returns:
            Random Point inside the polygon

        Example:
            >>> polygon = Polygon([Point(0, 0), Point(100, 0), Point(50, 100)])
            >>> point = polygon.randomPoint()
        """
        min_x, min_y, max_x, max_y = self.bounds()

        # Rejection sampling with max attempts
        max_attempts = 1000
        for _ in range(max_attempts):
            from shadowlib.types.point import Point

            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)
            point = Point(x, y)
            if self.contains(point):
                return point

        # Fallback to center if rejection sampling fails
        return self.center()

    def click(self, button: str = "left", randomize: bool = True) -> None:
        """
        Click within this polygon.

        Args:
            button: Mouse button ('left', 'right')
            randomize: If True, clicks at random point. If False, clicks at center.

        Example:
            >>> polygon = Polygon([Point(0, 0), Point(100, 0), Point(50, 100)])
            >>> polygon.click()  # Random click inside polygon
            >>> polygon.click(randomize=False)  # Click at center
        """
        point = self.randomPoint() if randomize else self.center()
        point.click(button=button)

    def hover(self, randomize: bool = True) -> None:
        """
        Move mouse to hover within this polygon.

        Args:
            randomize: If True, hovers at random point. If False, hovers at center.

        Example:
            >>> polygon = Polygon([Point(0, 0), Point(100, 0), Point(50, 100)])
            >>> polygon.hover()  # Hover at random point
        """
        point = self.randomPoint() if randomize else self.center()
        point.hover()

    def rightClick(self, randomize: bool = True) -> None:
        """
        Right-click within this polygon.

        Args:
            randomize: If True, clicks at random point. If False, clicks at center.

        Example:
            >>> polygon = Polygon([Point(0, 0), Point(100, 0), Point(50, 100)])
            >>> polygon.rightClick()
        """
        self.click(button="right", randomize=randomize)

    def __repr__(self) -> str:
        return f"Polygon({len(self.vertices)} vertices, area={self.area():.2f})"

    def debug(self, color: tuple[int, int, int] | str = "red", width: int = 2) -> None:
        """
        Visualize this polygon on a fresh capture of the game window.

        Args:
            color: Outline color (RGB tuple or name)
            width: Line width in pixels

        Example:
            >>> polygon = Polygon([Point(100, 100), Point(200, 100), Point(150, 200)])
            >>> polygon.debug()  # Shows polygon on game screenshot
        """
        from shadowlib._internal.visualizer import Visualizer

        viz = Visualizer()
        if viz.capture():
            viz.drawPolygon(self, color=color, width=width)
            viz.render()
