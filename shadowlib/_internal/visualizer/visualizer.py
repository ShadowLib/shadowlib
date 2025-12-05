"""Main Visualizer class for debug rendering."""

from PIL import Image, ImageDraw

from shadowlib.types.box import Box
from shadowlib.types.circle import Circle
from shadowlib.types.point import Point
from shadowlib.types.polygon import Polygon

from .capture import captureRuneLite
from .window import DebugWindow

# Type alias for color - RGB tuple or color name
Color = tuple[int, int, int] | str


class Visualizer:
    """
    Singleton debug visualizer for rendering overlays on RuneLite screenshots.

    Only one window is ever created, even with multiple Visualizer instances.

    Example:
        >>> from shadowlib._internal.visualizer import Visualizer
        >>>
        >>> viz = Visualizer()
        >>> viz.capture()  # Grab current RuneLite frame
        >>> # Drawing methods coming soon...
        >>> viz.render()   # Display in debug window
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """Actual initialization, runs once."""
        self._image: Image.Image | None = None
        self._draw: ImageDraw.ImageDraw | None = None
        self._debugWindow = DebugWindow()

    def capture(self) -> bool:
        """
        Capture screenshot of RuneLite window.

        Returns:
            True if capture succeeded, False otherwise

        Example:
            >>> viz = Visualizer()
            >>> if viz.capture():
            ...     viz.render()
        """
        image = captureRuneLite()
        if image is None:
            return False

        self._image = image
        self._draw = ImageDraw.Draw(self._image)
        return True

    def getImage(self) -> Image.Image | None:
        """
        Get the current captured image.

        Returns:
            PIL Image or None if no capture has been made
        """
        return self._image

    def setImage(self, image: Image.Image) -> None:
        """
        Set custom image (for testing or external sources).

        Args:
            image: PIL Image to use
        """
        self._image = image

    def render(self) -> bool:
        """
        Render current image to debug window.

        Creates window on first call, reuses existing window on subsequent calls.

        Returns:
            True if render succeeded, False if no image to render

        Example:
            >>> viz = Visualizer()
            >>> viz.capture()
            >>> viz.render()  # Opens/updates debug window
        """
        if self._image is None:
            return False

        self._debugWindow.render(self._image)
        return True

    def close(self) -> None:
        """Close the debug window."""
        self._debugWindow.close()

    def isWindowOpen(self) -> bool:
        """Check if debug window is currently open."""
        return self._debugWindow.isOpen()

    # ===== Drawing Methods =====

    def drawBox(
        self,
        box: Box,
        color: Color = "red",
        width: int = 2,
        fill: Color | None = None,
    ) -> None:
        """
        Draw a Box (rectangle) on the image.

        Args:
            box: Box to draw
            color: Outline color (RGB tuple or name)
            width: Line width in pixels
            fill: Optional fill color

        Example:
            >>> viz.capture()
            >>> viz.drawBox(Box(100, 100, 200, 200), color="green", width=3)
            >>> viz.render()
        """
        if self._draw is None:
            return
        self._draw.rectangle(
            [box.x1, box.y1, box.x2, box.y2], outline=color, width=width, fill=fill
        )

    def drawCircle(
        self,
        circle: Circle,
        color: Color = "red",
        width: int = 2,
        fill: Color | None = None,
    ) -> None:
        """
        Draw a Circle on the image.

        Args:
            circle: Circle to draw
            color: Outline color (RGB tuple or name)
            width: Line width in pixels
            fill: Optional fill color

        Example:
            >>> viz.capture()
            >>> viz.drawCircle(Circle(150, 150, 50), color="blue")
            >>> viz.render()
        """
        if self._draw is None:
            return
        x1 = circle.centerX - circle.radius
        y1 = circle.centerY - circle.radius
        x2 = circle.centerX + circle.radius
        y2 = circle.centerY + circle.radius
        self._draw.ellipse([x1, y1, x2, y2], outline=color, width=width, fill=fill)

    def drawPolygon(
        self,
        polygon: Polygon,
        color: Color = "red",
        width: int = 2,
        fill: Color | None = None,
    ) -> None:
        """
        Draw a Polygon on the image.

        Args:
            polygon: Polygon to draw
            color: Outline color (RGB tuple or name)
            width: Line width in pixels
            fill: Optional fill color

        Example:
            >>> viz.capture()
            >>> viz.drawPolygon(npc.hull, color="yellow")
            >>> viz.render()
        """
        if self._draw is None:
            return
        points = [(v.x, v.y) for v in polygon.vertices]
        self._draw.polygon(points, outline=color, width=width, fill=fill)

    def drawPoint(
        self,
        point: Point,
        color: Color = "red",
        size: int = 5,
    ) -> None:
        """
        Draw a Point as a small crosshair or dot.

        Args:
            point: Point to draw
            color: Color (RGB tuple or name)
            size: Size of the crosshair in pixels

        Example:
            >>> viz.capture()
            >>> viz.drawPoint(Point(150, 150), color="cyan", size=10)
            >>> viz.render()
        """
        if self._draw is None:
            return
        # Draw crosshair
        self._draw.line([(point.x - size, point.y), (point.x + size, point.y)], fill=color, width=2)
        self._draw.line([(point.x, point.y - size), (point.x, point.y + size)], fill=color, width=2)

    def drawLine(
        self,
        p1: Point,
        p2: Point,
        color: Color = "red",
        width: int = 2,
    ) -> None:
        """
        Draw a line between two points.

        Args:
            p1: Start point
            p2: End point
            color: Line color (RGB tuple or name)
            width: Line width in pixels

        Example:
            >>> viz.capture()
            >>> viz.drawLine(Point(0, 0), Point(100, 100), color="white")
            >>> viz.render()
        """
        if self._draw is None:
            return
        self._draw.line([(p1.x, p1.y), (p2.x, p2.y)], fill=color, width=width)

    def drawText(
        self,
        point: Point,
        text: str,
        color: Color = "white",
    ) -> None:
        """
        Draw text at a point.

        Args:
            point: Position for the text
            text: Text string to draw
            color: Text color (RGB tuple or name)

        Example:
            >>> viz.capture()
            >>> viz.drawText(Point(100, 100), "NPC Name", color="yellow")
            >>> viz.render()
        """
        if self._draw is None:
            return
        self._draw.text((point.x, point.y), text, fill=color)
