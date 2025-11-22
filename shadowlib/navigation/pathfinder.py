"""
Pathfinder for navigation.
"""

from typing import TYPE_CHECKING, Optional

from ..types.packed_position import PackedPosition
from ..types.path import Path

if TYPE_CHECKING:
    from ..client import Client


class Pathfinder:
    """Pathfinder for calculating routes."""

    def __init__(self, client: "Client"):
        """
        Initialize pathfinder.

        Args:
            client: The Client instance
        """
        self.client = client

    def getPath(
        self,
        destination_x: int,
        destination_y: int,
        destination_plane: int,
        use_transport: bool = True,
    ) -> Optional[Path]:
        """
        Calculate path to destination.

        Args:
            destination_x: Destination X coordinate
            destination_y: Destination Y coordinate
            destination_plane: Destination plane
            use_transport: If True, allows transport objects (doors, ladders, etc.)

        Returns:
            Path instance or None if no path found

        Example:
            >>> path = client.pathfinder.getPath(3200, 3200, 0)
            >>> if path:
            ...     print(f"Path length: {path.length()} tiles")
            ...     print(f"Duration: {path.getTotalSeconds():.1f}s")
            ...     print(f"Obstacles: {len(path.obstacles)}")
        """
        dest_packed = PackedPosition(destination_x, destination_y, destination_plane).packed

        result = self.client.api.invokeCustomMethod(
            target="BridgeHelpers",
            method="getPathWithObstaclesPacked",
            signature="(I)[B",
            args=[dest_packed],
            async_exec=True,
        )

        if not result or "path" not in result:
            return None

        return Path.fromDict(result)

    def getPathFromPosition(
        self,
        start_x: int,
        start_y: int,
        start_plane: int,
        destination_x: int,
        destination_y: int,
        destination_plane: int,
        use_transport: bool = True,
    ) -> Optional[Path]:
        """
        Calculate path from specific start position to destination.

        Args:
            start_x: Start X coordinate
            start_y: Start Y coordinate
            start_plane: Start plane
            destination_x: Destination X coordinate
            destination_y: Destination Y coordinate
            destination_plane: Destination plane
            use_transport: If True, allows transport objects

        Returns:
            Path instance or None if no path found

        Example:
            >>> path = client.pathfinder.getPathFromPosition(
            ...     3100, 3100, 0,  # Start
            ...     3200, 3200, 0   # Destination
            ... )
        """
        # For now, use the simpler method
        # TODO: Extend Java bridge to support custom start positions
        return self.getPath(destination_x, destination_y, destination_plane, use_transport)

    def canReach(
        self,
        destination_x: int,
        destination_y: int,
        destination_plane: int,
        use_transport: bool = True,
    ) -> bool:
        """
        Check if destination is reachable.

        Args:
            destination_x: Destination X coordinate
            destination_y: Destination Y coordinate
            destination_plane: Destination plane
            use_transport: If True, allows transport objects

        Returns:
            True if reachable

        Example:
            >>> if client.pathfinder.canReach(3200, 3200, 0):
            ...     print("GE is reachable!")
        """
        path = self.getPath(destination_x, destination_y, destination_plane, use_transport)
        return path is not None and not path.isEmpty()
