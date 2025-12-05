"""Screen capture utilities for RuneLite window."""

import subprocess

from PIL import Image
from Xlib import X, display

# Cached state for fast captures
_display: display.Display | None = None
_canvasWindow = None
_canvasSize: tuple[int, int] | None = None


def captureRuneLite(useCache: bool = True) -> Image.Image | None:
    """
    Capture screenshot of RuneLite window using Xlib (fast, ~3ms).

    Finds the actual game canvas window (not the frame) and captures it directly
    using X11's GetImage. Caches the window for faster subsequent captures.

    Args:
        useCache: If True, reuse cached window. Set False to re-detect.

    Returns:
        PIL Image of RuneLite window, or None if not found
    """
    global _display, _canvasWindow, _canvasSize

    # Initialize display if needed
    if _display is None:
        try:
            _display = display.Display()
        except Exception:
            return None

    # Use cached window if available
    if useCache and _canvasWindow is not None and _canvasSize is not None:
        img = _captureWindow(_canvasWindow, _canvasSize[0], _canvasSize[1])
        if img is not None:
            return img
        # Window may have closed, clear cache and retry
        _canvasWindow = None
        _canvasSize = None

    # Find the canvas window
    canvasId = _findCanvasWindow()
    if canvasId is None:
        return None

    wid, width, height = canvasId
    _canvasWindow = _display.create_resource_object("window", wid)
    _canvasSize = (width, height)

    return _captureWindow(_canvasWindow, width, height)


def clearCache() -> None:
    """Clear the cached window. Call this if RuneLite was restarted."""
    global _canvasWindow, _canvasSize
    _canvasWindow = None
    _canvasSize = None


def _captureWindow(window, width: int, height: int) -> Image.Image | None:
    """Capture window using Xlib XGetImage (fast, in-memory)."""
    try:
        raw = window.get_image(0, 0, width, height, X.ZPixmap, 0xFFFFFFFF)
        return Image.frombytes("RGB", (width, height), raw.data, "raw", "BGRX")
    except Exception:
        return None


def _findCanvasWindow() -> tuple[int, int, int] | None:
    """
    Find the RuneLite canvas window ID and dimensions.

    RuneLite creates multiple windows - we want the canvas (smallest non-trivial).

    Returns:
        Tuple of (window_id, width, height) or None if not found
    """
    global _display

    try:
        # Get all RuneLite windows using xdotool (reliable window search)
        result = subprocess.run(
            ["xdotool", "search", "--name", "RuneLite"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        windowIds = [int(wid) for wid in result.stdout.strip().split("\n")]

        # Find the canvas (smallest non-trivial window)
        candidates = []
        for wid in windowIds:
            try:
                win = _display.create_resource_object("window", wid)
                geo = win.get_geometry()
                if geo.width > 1 and geo.height > 1:
                    candidates.append((wid, geo.width, geo.height, geo.width * geo.height))
            except Exception:
                continue

        if not candidates:
            return None

        # Sort by area, return smallest
        candidates.sort(key=lambda x: x[3])
        wid, width, height, _ = candidates[0]
        return (wid, width, height)

    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return None
