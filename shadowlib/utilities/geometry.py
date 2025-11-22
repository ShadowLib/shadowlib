"""
Geometry utilities - points, areas, paths, and shapes with Shapely integration.

This module provides geometric primitives with:
- Efficient point sampling (uniform random, extensible for other distributions)
- Set-theoretic operations (union, intersection, difference, symmetric_difference)
- Constructive operations (buffer, convex_hull, simplify, envelope)
- Interactive methods (click, hover, right_click)
"""

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Tuple

from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box as shapely_box
from shapely.geometry.base import BaseGeometry

if TYPE_CHECKING:
    from ..io.io import IO


def _get_io() -> "IO":
    """Lazy import IO to avoid circular imports."""
    from ..io.io import IO

    # Create a global IO instance for geometry operations
    if not hasattr(_get_io, "_io_instance"):
        _get_io._io_instance = IO()
    return _get_io._io_instance


class Shape(ABC):
    """
    Base class for all geometric shapes with Shapely integration.

    Provides common operations for all shapes including:
    - Set-theoretic operations (union, intersection, difference, etc.)
    - Constructive operations (buffer, convex_hull, simplify, etc.)
    - Spatial queries (contains, area, bounds, etc.)
    - Interactive methods (click, hover, right_click)
    - Efficient point sampling with pluggable distributions
    """

    @property
    @abstractmethod
    def _shapely(self) -> BaseGeometry:
        """Return the underlying Shapely geometry."""
        pass

    # ========== Spatial Properties ==========

    def area(self) -> float:
        """Get the area of this shape."""
        return self._shapely.area

    def bounds(self) -> Tuple[float, float, float, float]:
        """
        Get the bounding box of this shape.

        Returns:
            Tuple of (minx, miny, maxx, maxy)
        """
        return self._shapely.bounds

    def contains(self, point: "Point") -> bool:
        """Check if a point is within this shape."""
        return self._shapely.contains(ShapelyPoint(point.x, point.y))

    def center(self) -> "Point":
        """Get the centroid of this shape."""
        centroid = self._shapely.centroid
        return Point(int(centroid.x), int(centroid.y))

    def length(self) -> float:
        """Get the perimeter/length of this shape."""
        return self._shapely.length

    # ========== Set-Theoretic Operations ==========

    def union(self, other: "Shape") -> "Shape":
        """
        Return the union of this shape with another.

        Args:
            other: Another shape to union with

        Returns:
            A new shape representing the union
        """
        result_geom = self._shapely.union(other._shapely)
        return _shapelyToShape(result_geom)

    def intersection(self, other: "Shape") -> "Shape":
        """
        Return the intersection of this shape with another.

        Args:
            other: Another shape to intersect with

        Returns:
            A new shape representing the intersection
        """
        result_geom = self._shapely.intersection(other._shapely)
        return _shapelyToShape(result_geom)

    def difference(self, other: "Shape") -> "Shape":
        """
        Return the difference of this shape minus another.

        Args:
            other: Another shape to subtract

        Returns:
            A new shape with the other shape subtracted
        """
        result_geom = self._shapely.difference(other._shapely)
        return _shapelyToShape(result_geom)

    def symmetricDifference(self, other: "Shape") -> "Shape":
        """
        Return the symmetric difference (XOR) of this shape with another.

        Args:
            other: Another shape

        Returns:
            A new shape representing points in either shape but not both
        """
        result_geom = self._shapely.symmetric_difference(other._shapely)
        return _shapelyToShape(result_geom)

    # Operator overloading for set operations
    def __and__(self, other: "Shape") -> "Shape":
        """Intersection operator: shape1 & shape2"""
        return self.intersection(other)

    def __or__(self, other: "Shape") -> "Shape":
        """Union operator: shape1 | shape2"""
        return self.union(other)

    def __sub__(self, other: "Shape") -> "Shape":
        """Difference operator: shape1 - shape2"""
        return self.difference(other)

    def __xor__(self, other: "Shape") -> "Shape":
        """Symmetric difference operator: shape1 ^ shape2"""
        return self.symmetricDifference(other)

    # ========== Constructive Operations ==========

    def buffer(self, distance: float, resolution: int = 16) -> "Shape":
        """
        Return a shape buffered by the given distance.

        Positive distance expands the shape, negative distance shrinks it.

        Args:
            distance: Distance to buffer (positive = expand, negative = shrink)
            resolution: Number of segments per quarter circle (default: 16)

        Returns:
            A new buffered shape
        """
        result_geom = self._shapely.buffer(distance, resolution=resolution)
        return _shapelyToShape(result_geom)

    def convexHull(self) -> "Polygon":
        """
        Return the convex hull of this shape.

        Returns:
            A Polygon representing the smallest convex shape containing all points
        """
        result_geom = self._shapely.convex_hull
        return _shapelyToShape(result_geom)

    def envelope(self) -> "Area":
        """
        Return the minimal axis-aligned bounding rectangle.

        Returns:
            An Area (rectangle) bounding this shape
        """
        minx, miny, maxx, maxy = self.bounds()
        return Area(int(minx), int(miny), int(maxx), int(maxy))

    def simplify(self, tolerance: float, preserve_topology: bool = True) -> "Shape":
        """
        Return a simplified version of this shape.

        Args:
            tolerance: Maximum distance for simplification
            preserve_topology: Whether to preserve topological validity

        Returns:
            A new simplified shape
        """
        result_geom = self._shapely.simplify(tolerance, preserve_topology=preserve_topology)
        return _shapelyToShape(result_geom)

    def minimumRotatedRectangle(self) -> "Quadrilateral":
        """
        Return the minimum rotated bounding rectangle.

        Returns:
            A Quadrilateral representing the smallest rotated rectangle
        """
        result_geom = self._shapely.minimum_rotated_rectangle
        return _shapelyToShape(result_geom)

    # ========== Point Sampling ==========

    def randomPoint(self, distribution: str = "uniform") -> "Point":
        """
        Generate a random point within this shape.

        Args:
            distribution: Distribution method. Currently supports:
                - 'uniform': Uniform random distribution (default)
                Future: 'gaussian', 'center_biased', etc.

        Returns:
            A random Point within this shape
        """
        if distribution == "uniform":
            return self._randomPointUniform()
        else:
            raise ValueError(f"Unknown distribution: {distribution}")

    def _randomPointUniform(self) -> "Point":
        """
        Generate a uniformly random point within this shape.

        Uses rejection sampling with the bounding box. Override for more
        efficient algorithms for specific shapes.
        """
        minx, miny, maxx, maxy = self.bounds()
        minx, miny, maxx, maxy = int(minx), int(miny), int(maxx), int(maxy)

        # Rejection sampling: try random points in bounding box until one is inside
        max_attempts = 1000
        for _ in range(max_attempts):
            x = random.randint(minx, maxx)
            y = random.randint(miny, maxy)
            point = Point(x, y)
            if self.contains(point):
                return point

        # Fallback to center if rejection sampling fails
        return self.center()

    # ========== Interactive Methods ==========

    def click(self, button: str = "left", duration: float = 0.2, randomize: bool = True) -> None:
        """
        Click within this shape.

        Args:
            button: Mouse button ('left', 'right', 'middle')
            duration: Time to take moving to the point (seconds)
            randomize: If True, clicks at a random point. If False, clicks at center.
        """
        point = self.randomPoint() if randomize else self.center()
        point.click(button=button, duration=duration)

    def hover(self, duration: float = 0.2, randomize: bool = True) -> None:
        """
        Move mouse to hover within this shape.

        Args:
            duration: Time to take moving to the point (seconds)
            randomize: If True, hovers at a random point. If False, hovers at center.
        """
        point = self.randomPoint() if randomize else self.center()
        point.hover(duration=duration)

    def rightClick(self, duration: float = 0.2, randomize: bool = True) -> None:
        """
        Right-click within this shape.

        Args:
            duration: Time to take moving to the point (seconds)
            randomize: If True, clicks at a random point. If False, clicks at center.
        """
        self.click(button="right", duration=duration, randomize=randomize)


@dataclass
class Point(Shape):
    """Represents a 2D point."""

    x: int
    y: int

    @property
    def _shapely(self) -> ShapelyPoint:
        """Return the underlying Shapely point."""
        if not hasattr(self, "_shapely_cache"):
            self._shapely_cache = ShapelyPoint(self.x, self.y)
        return self._shapely_cache

    def distanceTo(self, other: "Point") -> float:
        """Calculate distance to another point."""
        return self._shapely.distance(other._shapely)

    def contains(self, point: "Point") -> bool:
        """A point only contains itself."""
        return self.x == point.x and self.y == point.y

    def _randomPointUniform(self) -> "Point":
        """A point's random point is itself."""
        return self

    def click(self, button: str = "left", duration: float = 0.2, randomize: bool = True) -> None:
        """
        Click at this point.

        Args:
            button: Mouse button ('left', 'right', 'middle')
            duration: Time to take moving to the point (seconds)
            randomize: Ignored for points
        """
        io = _get_io()
        io.mouse.move(self.x, self.y, duration=duration)
        io.mouse.click(button=button)

    def hover(self, duration: float = 0.2, randomize: bool = True) -> None:
        """
        Move mouse to hover over this point.

        Args:
            duration: Time to take moving to the point (seconds)
            randomize: Ignored for points
        """
        io = _get_io()
        io.mouse.move(self.x, self.y, duration=duration)

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


@dataclass
class Point3D:
    """Represents a 3D point (z-coordinates ignored for 2D operations)."""

    x: int
    y: int
    z: int

    def distanceTo(self, other: "Point3D") -> float:
        """Calculate 3D distance to another point."""
        from .math import distance3d

        return distance3d((self.x, self.y, self.z), (other.x, other.y, other.z))

    def to2d(self) -> Point:
        """Convert to 2D point (dropping z coordinate)."""
        return Point(self.x, self.y)

    def __repr__(self) -> str:
        return f"Point3D({self.x}, {self.y}, {self.z})"


@dataclass
class Area(Shape):
    """Represents a rectangular area (axis-aligned)."""

    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self):
        """Ensure coordinates are ordered correctly."""
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
        if self.y1 > self.y2:
            self.y1, self.y2 = self.y2, self.y1

    @property
    def _shapely(self) -> ShapelyPolygon:
        """Return the underlying Shapely polygon."""
        if not hasattr(self, "_shapely_cache"):
            self._shapely_cache = shapely_box(self.x1, self.y1, self.x2, self.y2)
        return self._shapely_cache

    def contains(self, point: Point) -> bool:
        """Check if point is within area."""
        return self.x1 <= point.x < self.x2 and self.y1 <= point.y < self.y2

    def _random_point_uniform(self) -> Point:
        """Efficiently generate uniform random point in rectangle."""
        return Point(random.randrange(self.x1, self.x2), random.randrange(self.y1, self.y2))

    def width(self) -> int:
        """Get width of the rectangle."""
        return self.x2 - self.x1

    def height(self) -> int:
        """Get height of the rectangle."""
        return self.y2 - self.y1

    def __repr__(self) -> str:
        return f"Area({self.x1}, {self.y1}) to ({self.x2}, {self.y2})"


@dataclass
class Circle(Shape):
    """Represents a circle."""

    center_x: int
    center_y: int
    radius: float

    @property
    def _shapely(self) -> ShapelyPolygon:
        """Return the underlying Shapely polygon (approximated circle)."""
        if not hasattr(self, "_shapely_cache"):
            # Create circle as buffered point
            center = ShapelyPoint(self.center_x, self.center_y)
            self._shapely_cache = center.buffer(self.radius, resolution=32)
        return self._shapely_cache

    def contains(self, point: Point) -> bool:
        """Check if point is within circle."""
        dx = point.x - self.center_x
        dy = point.y - self.center_y
        return math.sqrt(dx * dx + dy * dy) <= self.radius

    def _random_point_uniform(self) -> Point:
        """
        Efficiently generate uniform random point in circle.

        Uses the polar method with sqrt for uniform distribution.
        """
        # Use sqrt to get uniform distribution (not just random angle/radius)
        r = self.radius * math.sqrt(random.random())
        theta = random.uniform(0, 2 * math.pi)

        x = self.center_x + int(r * math.cos(theta))
        y = self.center_y + int(r * math.sin(theta))

        return Point(x, y)

    def center(self) -> Point:
        """Get the center point of the circle."""
        return Point(self.center_x, self.center_y)

    def __repr__(self) -> str:
        return f"Circle(center=({self.center_x}, {self.center_y}), radius={self.radius})"


@dataclass
class Triangle(Shape):
    """Represents a triangle defined by three points."""

    p1: Point
    p2: Point
    p3: Point

    @property
    def _shapely(self) -> ShapelyPolygon:
        """Return the underlying Shapely polygon."""
        if not hasattr(self, "_shapely_cache"):
            coords = [(self.p1.x, self.p1.y), (self.p2.x, self.p2.y), (self.p3.x, self.p3.y)]
            self._shapely_cache = ShapelyPolygon(coords)
        return self._shapely_cache

    def _random_point_uniform(self) -> Point:
        """
        Efficiently generate uniform random point in triangle.

        Uses barycentric coordinates for true uniform distribution.
        """
        # Generate random barycentric coordinates
        r1 = random.random()
        r2 = random.random()

        # Ensure point is in triangle (fold if outside)
        if r1 + r2 > 1:
            r1 = 1 - r1
            r2 = 1 - r2

        r3 = 1 - r1 - r2

        # Compute point using barycentric coordinates
        # Use round instead of int to avoid boundary issues
        x = round(r1 * self.p1.x + r2 * self.p2.x + r3 * self.p3.x)
        y = round(r1 * self.p1.y + r2 * self.p2.y + r3 * self.p3.y)

        point = Point(x, y)

        # Ensure point is actually in triangle (handle edge cases)
        if not self._shapely.contains(point._shapely):
            # Fall back to centroid if rounding pushed us outside
            return self.center()

        return point

    def __repr__(self) -> str:
        return f"Triangle({self.p1}, {self.p2}, {self.p3})"


@dataclass
class Quadrilateral(Shape):
    """Represents a quadrilateral defined by four arbitrary points."""

    p1: Point
    p2: Point
    p3: Point
    p4: Point

    @property
    def _shapely(self) -> ShapelyPolygon:
        """Return the underlying Shapely polygon."""
        if not hasattr(self, "_shapely_cache"):
            coords = [
                (self.p1.x, self.p1.y),
                (self.p2.x, self.p2.y),
                (self.p3.x, self.p3.y),
                (self.p4.x, self.p4.y),
            ]
            self._shapely_cache = ShapelyPolygon(coords)
        return self._shapely_cache

    def __repr__(self) -> str:
        return f"Quadrilateral({self.p1}, {self.p2}, {self.p3}, {self.p4})"


@dataclass
class Polygon(Shape):
    """Represents an arbitrary polygon defined by n points."""

    vertices: List[Point]

    def __post_init__(self):
        """Validate polygon has at least 3 vertices."""
        if len(self.vertices) < 3:
            raise ValueError("Polygon must have at least 3 vertices")

    @property
    def _shapely(self) -> ShapelyPolygon:
        """Return the underlying Shapely polygon."""
        if not hasattr(self, "_shapely_cache"):
            coords = [(p.x, p.y) for p in self.vertices]
            self._shapely_cache = ShapelyPolygon(coords)
        return self._shapely_cache

    def __repr__(self) -> str:
        return f"Polygon({len(self.vertices)} vertices, area={self.area():.2f})"


class Path:
    """Represents a path as a series of points."""

    def __init__(self, points: List[Point]):
        """
        Initialize path.

        Args:
            points: List of points making up the path
        """
        self.points = points

    def length(self) -> float:
        """Calculate total path length."""
        if len(self.points) < 2:
            return 0.0

        total = 0.0
        for i in range(len(self.points) - 1):
            total += self.points[i].distance_to(self.points[i + 1])
        return total

    def reverse(self) -> "Path":
        """Get reversed path."""
        return Path(list(reversed(self.points)))

    def __repr__(self) -> str:
        return f"Path({len(self.points)} points, length={self.length():.2f})"


def _shapelyToShape(geom: BaseGeometry) -> Shape:
    """
    Convert a Shapely geometry back to our Shape classes.

    Args:
        geom: Shapely geometry object

    Returns:
        Appropriate Shape subclass
    """
    from shapely.geometry import GeometryCollection, MultiPolygon
    from shapely.geometry import Point as ShapelyPoint
    from shapely.geometry import Polygon as ShapelyPolygon

    if isinstance(geom, ShapelyPoint):
        return Point(int(geom.x), int(geom.y))
    elif isinstance(geom, ShapelyPolygon):
        coords = list(geom.exterior.coords[:-1])  # Exclude closing point
        if len(coords) == 3:
            return Triangle(
                Point(int(coords[0][0]), int(coords[0][1])),
                Point(int(coords[1][0]), int(coords[1][1])),
                Point(int(coords[2][0]), int(coords[2][1])),
            )
        elif len(coords) == 4:
            # Check if it's axis-aligned rectangle
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            if len(set(xs)) == 2 and len(set(ys)) == 2:
                return Area(int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            else:
                return Quadrilateral(
                    Point(int(coords[0][0]), int(coords[0][1])),
                    Point(int(coords[1][0]), int(coords[1][1])),
                    Point(int(coords[2][0]), int(coords[2][1])),
                    Point(int(coords[3][0]), int(coords[3][1])),
                )
        else:
            points = [Point(int(c[0]), int(c[1])) for c in coords]
            return Polygon(points)
    elif isinstance(geom, MultiPolygon):
        # For MultiPolygon, use the convex hull to get a single polygon
        # This is a reasonable approximation for most use cases
        return _shapely_to_shape(geom.convex_hull)
    elif isinstance(geom, GeometryCollection):
        # For GeometryCollection, also use convex hull
        if geom.is_empty:
            # Return a minimal point if empty
            return Point(0, 0)
        return _shapely_to_shape(geom.convex_hull)
    else:
        # For other geometry types, wrap in a generic polygon
        if hasattr(geom, "exterior"):
            coords = list(geom.exterior.coords[:-1])
            points = [Point(int(c[0]), int(c[1])) for c in coords]
            return Polygon(points)
        raise ValueError(f"Cannot convert {type(geom)} to Shape")


def createGrid(
    start_x: int,
    start_y: int,
    width: int,
    height: int,
    columns: int,
    rows: int,
    spacing_x: int = 0,
    spacing_y: int = 0,
    padding: int = 0,
) -> List[Area]:
    """
    Create a grid of Areas.

    Args:
        start_x: X coordinate of the top-left corner of the first area
        start_y: Y coordinate of the top-left corner of the first area
        width: Width of each area in pixels
        height: Height of each area in pixels
        columns: Number of columns in the grid
        rows: Number of rows in the grid
        spacing_x: Horizontal spacing between areas (default: 0)
        spacing_y: Vertical spacing between areas (default: 0)
        padding: Inner padding for each area in pixels (shrinks area on all sides, default: 0)

    Returns:
        List of Area objects in row-major order (left to right, top to bottom)

    Example:
        # Create a 4x7 inventory grid
        slots = createGrid(563, 213, 36, 32, columns=4, rows=7, spacing_x=6, spacing_y=4)
        # slots[0] is top-left, slots[3] is top-right, slots[4] is second row left, etc.

        # Create grid with 2px padding to avoid edge clicks
        slots = createGrid(563, 213, 36, 32, columns=4, rows=7, spacing_x=6, spacing_y=4, padding=2)
    """
    areas = []
    for row in range(rows):
        for col in range(columns):
            x1 = start_x + col * (width + spacing_x)
            y1 = start_y + row * (height + spacing_y)
            x2 = x1 + width
            y2 = y1 + height

            # Apply padding (shrink area on all sides)
            if padding > 0:
                x1 += padding
                y1 += padding
                x2 -= padding
                y2 -= padding

            areas.append(Area(x1, y1, x2, y2))
    return areas


class NullShape(Shape):
    """
    Null Object pattern for Shape - safe to call methods but does nothing.

    Used when a shape cannot be found (e.g., object offscreen) to avoid
    None checks everywhere. All methods are safe to call and return sensible
    defaults without throwing errors.

    Example:
        >>> clickbox = obj.get_clickbox()  # Returns NullShape if offscreen
        >>> clickbox.hover()  # Safe - does nothing
        >>> clickbox.click()  # Safe - does nothing
        >>> area = clickbox.area()  # Returns 0.0
    """

    @property
    def _shapely(self) -> BaseGeometry:
        """Return empty point as the shapely representation."""
        return ShapelyPoint()

    def area(self) -> float:
        """Return 0 area."""
        return 0.0

    def bounds(self) -> Tuple[float, float, float, float]:
        """Return (0, 0, 0, 0) bounds."""
        return (0.0, 0.0, 0.0, 0.0)

    def contains(self, point: "Point") -> bool:
        """Always return False - null shape contains nothing."""
        return False

    def center(self) -> "Point":
        """Return origin point."""
        return Point(0, 0)

    def length(self) -> float:
        """Return 0 length."""
        return 0.0

    def union(self, other: "Shape") -> "Shape":
        """Return the other shape unchanged."""
        return other

    def intersection(self, other: "Shape") -> "Shape":
        """Return null shape - no intersection."""
        return NullShape()

    def difference(self, other: "Shape") -> "Shape":
        """Return null shape - nothing to subtract from."""
        return NullShape()

    def symmetricDifference(self, other: "Shape") -> "Shape":
        """Return the other shape unchanged."""
        return other

    def buffer(self, distance: float, **kwargs) -> "Shape":
        """Return null shape - buffering nothing gives nothing."""
        return NullShape()

    def convexHull(self) -> "Shape":
        """Return null shape."""
        return NullShape()

    def envelope(self) -> "Shape":
        """Return null shape."""
        return NullShape()

    def simplify(self, tolerance: float, preserve_topology: bool = True) -> "Shape":
        """Return null shape."""
        return NullShape()

    def minimumRotatedRectangle(self) -> "Shape":
        """Return null shape."""
        return NullShape()

    def randomPoint(self, distribution: str = "uniform") -> "Point":
        """Return origin point."""
        return Point(0, 0)

    def _randomPointUniform(self) -> "Point":
        """Return origin point."""
        return Point(0, 0)

    def click(self, button: str = "left", duration: float = 0.2, randomize: bool = True):
        """Do nothing - safe to call."""
        pass

    def hover(self, duration: float = 0.2, randomize: bool = True):
        """Do nothing - safe to call."""
        pass

    def rightClick(self, duration: float = 0.2, randomize: bool = True):
        """Do nothing - safe to call."""
        pass

    def __bool__(self) -> bool:
        """Return False so null shapes are falsy in boolean context."""
        return False

    def __repr__(self) -> str:
        """String representation."""
        return "NullShape()"
