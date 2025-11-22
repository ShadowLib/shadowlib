"""
Player state middleware.

Provides clean access to player properties via cache.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from ..client import Client


class Player:
    """Player state accessor."""

    def __init__(self, client: "Client"):
        """
        Initialize player accessor.

        Args:
            client: The Client instance
        """
        self.client = client
        self._cached_state: Dict[str, Any] = {}
        self._cached_tick: int = -1

    def _getState(self) -> Dict[str, Any]:
        """
        Get cached player state (refreshed per tick).

        Returns:
            Player state dict
        """
        current_tick = self.client.cache.tick

        # Return cached if same tick
        if self._cached_tick == current_tick and self._cached_state:
            return self._cached_state

        # Refresh from cache
        self._cached_state = self.client.cache.position.copy()
        self._cached_tick = current_tick

        return self._cached_state

    @property
    def position(self) -> Dict[str, int]:
        """
        Get player position.

        Returns:
            Dict with 'x', 'y', 'plane' keys

        Example:
            >>> pos = client.player.position
            >>> print(f"Player at ({pos['x']}, {pos['y']}, {pos['plane']})")
        """
        return self._getState()

    @property
    def x(self) -> int:
        """Get player X coordinate."""
        return self._getState().get("x", 0)

    @property
    def y(self) -> int:
        """Get player Y coordinate."""
        return self._getState().get("y", 0)

    @property
    def plane(self) -> int:
        """Get player plane level."""
        return self._getState().get("plane", 0)

    @property
    def energy(self) -> int:
        """
        Get run energy (0-10000).

        Returns:
            Run energy value

        Example:
            >>> energy = client.player.energy
            >>> print(f"Run energy: {energy / 100}%")
        """
        return self.client.cache.energy

    @property
    def tick(self) -> int:
        """
        Get current game tick.

        Returns:
            Current tick number

        Example:
            >>> tick = client.player.tick
        """
        return self.client.cache.tick

    def distanceTo(self, x: int, y: int) -> int:
        """
        Calculate distance from player to coordinates.

        Args:
            x: Target X coordinate
            y: Target Y coordinate

        Returns:
            Chebyshev distance in tiles

        Example:
            >>> distance = client.player.distanceTo(3200, 3200)
        """
        dx = abs(self.x - x)
        dy = abs(self.y - y)
        return max(dx, dy)

    def isAt(self, x: int, y: int, plane: Optional[int] = None) -> bool:
        """
        Check if player is at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            plane: Optional plane (if None, ignores plane)

        Returns:
            True if player is at position

        Example:
            >>> if client.player.isAt(3200, 3200):
            ...     print("At Grand Exchange")
        """
        if self.x != x or self.y != y:
            return False

        if plane is not None and self.plane != plane:
            return False

        return True

    def isNearby(self, x: int, y: int, radius: int, plane: Optional[int] = None) -> bool:
        """
        Check if player is within radius of coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            radius: Maximum distance in tiles
            plane: Optional plane (if None, ignores plane)

        Returns:
            True if within radius

        Example:
            >>> if client.player.isNearby(3200, 3200, radius=10):
            ...     print("Near Grand Exchange")
        """
        if plane is not None and self.plane != plane:
            return False

        return self.distanceTo(x, y) <= radius
