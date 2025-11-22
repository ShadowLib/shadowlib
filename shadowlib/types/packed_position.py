"""
PackedPosition type for efficient OSRS coordinate storage.

Positions are packed into 32-bit integers:
- Bits [31-30]: Plane (2 bits, range 0-3)
- Bits [29-15]: X coordinate (15 bits, range 0-32767)
- Bits [14-0]: Y coordinate (15 bits, range 0-32767)
"""

from typing import Tuple


class PackedPosition:
    """
    Efficient packed position representation for OSRS coordinates.

    Internally stores (x, y, plane) as a single 32-bit integer.
    """

    __slots__ = ("_packed",)

    def __init__(self, x: int = 0, y: int = 0, plane: int = 0):
        """
        Create a packed position.

        Args:
            x: X coordinate (0-32767)
            y: Y coordinate (0-32767)
            plane: Plane level (0-3)
        """
        if not (0 <= x <= 32767):
            raise ValueError(f"X out of range: {x} (must be 0-32767)")
        if not (0 <= y <= 32767):
            raise ValueError(f"Y out of range: {y} (must be 0-32767)")
        if not (0 <= plane <= 3):
            raise ValueError(f"Plane out of range: {plane} (must be 0-3)")

        self._packed = ((plane & 0x3) << 30) | ((y & 0x7FFF) << 15) | (x & 0x7FFF)

    @classmethod
    def fromPacked(cls, packed: int) -> "PackedPosition":
        """
        Create from a packed integer.

        Args:
            packed: Packed 32-bit position integer

        Returns:
            PackedPosition instance
        """
        pos = cls.__new__(cls)
        pos._packed = packed
        return pos

    @property
    def x(self) -> int:
        """Get X coordinate."""
        return self._packed & 0x7FFF

    @property
    def y(self) -> int:
        """Get Y coordinate."""
        return (self._packed >> 15) & 0x7FFF

    @property
    def plane(self) -> int:
        """Get plane level."""
        return (self._packed >> 30) & 0x3

    @property
    def packed(self) -> int:
        """Get packed integer representation."""
        return self._packed

    def unpack(self) -> Tuple[int, int, int]:
        """
        Unpack to (x, y, plane) tuple.

        Returns:
            Tuple of (x, y, plane)
        """
        return (self.x, self.y, self.plane)

    def distanceTo(self, other: "PackedPosition") -> int:
        """
        Calculate Chebyshev distance to another position.

        Args:
            other: Other PackedPosition

        Returns:
            Distance in tiles (max of dx, dy)
        """
        dx = abs(self.x - other.x)
        dy = abs(self.y - other.y)
        return max(dx, dy)

    def isNearby(self, other: "PackedPosition", radius: int, same_plane: bool = True) -> bool:
        """
        Check if position is within radius of another.

        Args:
            other: Other PackedPosition
            radius: Maximum distance in tiles
            same_plane: If True, positions must be on same plane

        Returns:
            True if within radius
        """
        if same_plane and self.plane != other.plane:
            return False

        return self.distanceTo(other) <= radius

    def __eq__(self, other) -> bool:
        if isinstance(other, PackedPosition):
            return self._packed == other._packed
        return False

    def __hash__(self) -> int:
        return self._packed

    def __repr__(self) -> str:
        return f"PackedPosition(x={self.x}, y={self.y}, plane={self.plane})"

    def __str__(self) -> str:
        return f"({self.x}, {self.y}, {self.plane})"
