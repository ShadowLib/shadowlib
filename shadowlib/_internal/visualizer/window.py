"""Persistent debug window manager using Tkinter."""

import io
import tkinter as tk
from typing import ClassVar

from PIL import Image


class DebugWindow:
    """
    Singleton debug window that persists across render calls.

    Uses Tkinter for zero external dependencies beyond Pillow.
    Window is created on first render and reused for subsequent calls.
    """

    _instance: ClassVar["DebugWindow | None"] = None
    _root: ClassVar[tk.Tk | None] = None
    _label: ClassVar[tk.Label | None] = None
    _photoImage: ClassVar[tk.PhotoImage | None] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensureWindow(self, width: int, height: int) -> None:
        """
        Ensure window exists, create if needed.

        Args:
            width: Window width
            height: Window height
        """
        if DebugWindow._root is None or not self._isWindowAlive():
            self._createWindow(width, height)
        else:
            # Resize if needed
            currentWidth = DebugWindow._root.winfo_width()
            currentHeight = DebugWindow._root.winfo_height()
            if currentWidth != width or currentHeight != height:
                DebugWindow._root.geometry(f"{width}x{height}")

    def _isWindowAlive(self) -> bool:
        """Check if the Tkinter window still exists."""
        try:
            if DebugWindow._root is None:
                return False
            DebugWindow._root.winfo_exists()
            return True
        except tk.TclError:
            return False

    def _createWindow(self, width: int, height: int) -> None:
        """
        Create new Tkinter window.

        Args:
            width: Window width
            height: Window height
        """
        DebugWindow._root = tk.Tk()
        DebugWindow._root.title("ShadowLib Debug Visualizer")
        DebugWindow._root.geometry(f"{width}x{height}")
        DebugWindow._root.resizable(False, False)

        # Create label to hold image
        DebugWindow._label = tk.Label(DebugWindow._root)
        DebugWindow._label.pack(fill=tk.BOTH, expand=True)

        # Handle window close - destroy and reset references
        DebugWindow._root.protocol("WM_DELETE_WINDOW", self._onClose)

    def _onClose(self) -> None:
        """Handle window close button - destroy and reset references."""
        if DebugWindow._root is not None:
            DebugWindow._root.destroy()
            DebugWindow._root = None
            DebugWindow._label = None
            DebugWindow._photoImage = None

    def _pilToTkPhoto(self, image: Image.Image) -> tk.PhotoImage:
        """
        Convert PIL Image to Tkinter PhotoImage without ImageTk.

        Uses PPM format as intermediate since tk.PhotoImage supports it natively.

        Args:
            image: PIL Image to convert

        Returns:
            Tkinter PhotoImage
        """
        # Convert to RGB if necessary (PhotoImage doesn't support RGBA well)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Save to PPM format in memory (Tkinter natively supports PPM)
        buffer = io.BytesIO()
        image.save(buffer, format="PPM")
        ppmData = buffer.getvalue()

        return tk.PhotoImage(data=ppmData)

    def render(self, image: Image.Image) -> None:
        """
        Render image to debug window.

        Creates window on first call, updates existing window on subsequent calls.

        Args:
            image: PIL Image to display
        """
        width, height = image.size
        self._ensureWindow(width, height)

        # Convert to PhotoImage and update label
        # Keep reference to prevent garbage collection
        DebugWindow._photoImage = self._pilToTkPhoto(image)
        DebugWindow._label.configure(image=DebugWindow._photoImage)

        # Process pending events and update display (non-blocking)
        DebugWindow._root.update_idletasks()
        DebugWindow._root.update()

    def close(self) -> None:
        """Close and destroy the debug window."""
        self._onClose()

    def isOpen(self) -> bool:
        """Check if debug window is currently open."""
        return self._isWindowAlive()
