"""
Path and obstacle types for navigation.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .packed_position import PackedPosition


@dataclass
class PathObstacle:
    """
    Represents an obstacle along a path.

    Attributes:
        origin: Origin position (packed)
        dest: Destination position (packed)
        type: Obstacle type (TRANSPORT, TELEPORTATION_SPELL, AGILITY_SHORTCUT, etc.)
        duration: Duration in ticks
        displayInfo: Display name (e.g., "Lumbridge Home Teleport")
        objectInfo: Object interaction info (e.g., "Open Door 12348")
    """

    origin: PackedPosition
    dest: PackedPosition
    type: str
    duration: int
    displayInfo: Optional[str]
    objectInfo: Optional[str]

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "PathObstacle":
        """
        Create PathObstacle from dict.

        Args:
            data: Raw obstacle data from Java

        Returns:
            PathObstacle instance
        """
        return cls(
            origin=PackedPosition.fromPacked(data["origin"]),
            dest=PackedPosition.fromPacked(data["dest"]),
            type=data["type"],
            duration=data["duration"],
            displayInfo=data.get("displayInfo"),
            objectInfo=data.get("objectInfo"),
        )

    def __repr__(self) -> str:
        name = self.displayInfo or self.objectInfo or self.type
        return f"PathObstacle({name}, {self.duration} ticks)"


class Path:
    """
    Represents a navigation path with obstacles.

    Provides access to path tiles and obstacles.
    """

    def __init__(self, tiles: List[PackedPosition], obstacles: List[PathObstacle]):
        """
        Initialize path.

        Args:
            tiles: List of positions along the path
            obstacles: List of obstacles along the path
        """
        self._tiles = tiles
        self._obstacles = obstacles

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "Path":
        """
        Create Path from Java response dict.

        Args:
            data: Response from getPathWithObstacles

        Returns:
            Path instance

        Example:
            >>> result = api.invokeCustomMethod(...)
            >>> path = Path.fromDict(result)
        """
        # Parse tiles
        tiles = [PackedPosition.fromPacked(packed) for packed in data["path"]]

        # Parse obstacles
        obstacles = [PathObstacle.fromDict(obs) for obs in data["obstacles"]]

        return cls(tiles, obstacles)

    @property
    def tiles(self) -> List[PackedPosition]:
        """Get all tiles in path."""
        return self._tiles

    @property
    def obstacles(self) -> List[PathObstacle]:
        """Get all obstacles in path."""
        return self._obstacles

    def length(self) -> int:
        """Get path length in tiles."""
        return len(self._tiles)

    def isEmpty(self) -> bool:
        """Check if path is empty."""
        return len(self._tiles) == 0

    def getStart(self) -> Optional[PackedPosition]:
        """Get start position."""
        return self._tiles[0] if self._tiles else None

    def getEnd(self) -> Optional[PackedPosition]:
        """Get end position (destination)."""
        return self._tiles[-1] if self._tiles else None

    def getNextTile(self, current: PackedPosition) -> Optional[PackedPosition]:
        """
        Get next tile from current position.

        Args:
            current: Current position

        Returns:
            Next tile or None if at end
        """
        try:
            idx = self._tiles.index(current)
            if idx < len(self._tiles) - 1:
                return self._tiles[idx + 1]
        except ValueError:
            pass
        return None

    def getObstacleAt(self, position: PackedPosition) -> Optional[PathObstacle]:
        """
        Get obstacle at position (if any).

        Args:
            position: Position to check

        Returns:
            PathObstacle or None
        """
        for obstacle in self._obstacles:
            if obstacle.origin == position:
                return obstacle
        return None

    def hasObstacles(self) -> bool:
        """Check if path has any obstacles."""
        return len(self._obstacles) > 0

    def getTotalDuration(self) -> int:
        """
        Get total estimated duration in ticks.

        Includes walking time + obstacle durations.

        Returns:
            Total ticks
        """
        # Approximate: 1 tile = 1 tick walking
        walk_ticks = len(self._tiles)
        obstacle_ticks = sum(obs.duration for obs in self._obstacles)
        return walk_ticks + obstacle_ticks

    def getTotalSeconds(self) -> float:
        """
        Get total estimated duration in seconds.

        Returns:
            Total seconds (ticks * 0.6)
        """
        return self.getTotalDuration() * 0.6

    def __len__(self) -> int:
        """Support len() builtin."""
        return len(self._tiles)

    def __iter__(self):
        """Iterate over tiles."""
        return iter(self._tiles)

    def __getitem__(self, index):
        """Support indexing."""
        return self._tiles[index]

    def __repr__(self) -> str:
        return (
            f"Path({len(self._tiles)} tiles, {len(self._obstacles)} obstacles, "
            f"~{self.getTotalSeconds():.1f}s)"
        )
