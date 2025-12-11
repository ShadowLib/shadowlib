"""
Path and obstacle types for navigation.

Uses numpy arrays for efficient coordinate storage and projection integration.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List

import numpy as np

from .packed_position import PackedPosition

if TYPE_CHECKING:
    from shadowlib.types import Point, Quad
    from shadowlib.world.projection import TileGrid


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
    displayInfo: str | None
    objectInfo: str | None

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
    Navigation path with numpy-backed coordinate storage.

    Stores path tiles as packed integers in a numpy array for efficient
    vectorized operations. Integrates with TileGrid for screen projections.

    Example:
        >>> from shadowlib.navigation.pathfinder import pathfinder
        >>> path = pathfinder.getPath(3200, 3200, 0)
        >>> if path:
        ...     # Vectorized world coordinates
        ...     print(f"X range: {path.worldX.min()} - {path.worldX.max()}")
        ...     # Get screen coordinates for visible tiles
        ...     screenX, screenY, mask = path.getScreenCoords()
        ...     visibleCount = mask.sum()
    """

    __slots__ = ("_packed", "_obstacles")

    def __init__(self, packed: np.ndarray, obstacles: List[PathObstacle]):
        """
        Initialize path.

        Args:
            packed: Numpy array of packed position integers
            obstacles: List of obstacles along the path
        """
        self._packed = packed.astype(np.int32)
        self._obstacles = obstacles

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "Path":
        """
        Create Path from Java response dict.

        Converts the packed integer array directly to numpy - no loops.

        Args:
            data: Response from getPathWithObstacles

        Returns:
            Path instance

        Example:
            >>> result = api.invokeCustomMethod(...)
            >>> path = Path.fromDict(result)
        """
        # Direct numpy conversion - instant for any size
        packed = np.array(data["path"], dtype=np.int32)

        # Obstacles are few, so list comprehension is fine
        obstacles = [PathObstacle.fromDict(obs) for obs in data.get("obstacles", [])]

        return cls(packed, obstacles)

    # -------------------------------------------------------------------------
    # Vectorized coordinate access
    # -------------------------------------------------------------------------

    @property
    def worldX(self) -> np.ndarray:
        """World X coordinates (vectorized). Shape: [length]. X is bits 0-14."""
        return (self._packed & 0x7FFF).astype(np.int32)

    @property
    def worldY(self) -> np.ndarray:
        """World Y coordinates (vectorized). Shape: [length]. Y is bits 15-29."""
        return ((self._packed >> 15) & 0x7FFF).astype(np.int32)

    @property
    def plane(self) -> np.ndarray:
        """Plane values (vectorized). Shape: [length]."""
        return ((self._packed >> 30) & 0x3).astype(np.int32)

    @property
    def packed(self) -> np.ndarray:
        """Raw packed integers. Shape: [length]."""
        return self._packed

    # -------------------------------------------------------------------------
    # TileGrid integration for screen projection
    # -------------------------------------------------------------------------

    def _getTileGrid(self) -> "TileGrid | None":
        """Get cached TileGrid from projection singleton."""
        from shadowlib.world.projection import projection

        return projection.tiles

    def getSceneCoords(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Convert world coords to scene coords.

        Returns:
            Tuple of (sceneX, sceneY, inSceneMask) numpy arrays.
            inSceneMask is True for tiles within the loaded scene.
        """
        grid = self._getTileGrid()
        if grid is None:
            empty = np.array([], dtype=np.int32)
            return empty, empty, np.array([], dtype=np.bool_)

        sceneX = self.worldX - grid.baseX
        sceneY = self.worldY - grid.baseY

        inScene = (sceneX >= 0) & (sceneX < grid.sizeX) & (sceneY >= 0) & (sceneY < grid.sizeY)

        return sceneX, sceneY, inScene

    def getScreenCoords(self, margin: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get screen coordinates for path tiles using cached TileGrid.

        Only tiles within the loaded scene get valid screen coords.
        Uses TileGrid's precomputed tile centers - no re-projection.

        Args:
            margin: Extra pixels around viewport for visibility check

        Returns:
            Tuple of (screenX, screenY, visibleMask) numpy arrays.
            visibleMask is True for tiles that are on screen.

        Example:
            >>> screenX, screenY, visible = path.getScreenCoords()
            >>> if visible.any():
            ...     # Get first visible tile's screen position
            ...     idx = np.where(visible)[0][0]
            ...     print(f"First visible at ({screenX[idx]}, {screenY[idx]})")
        """
        grid = self._getTileGrid()
        if grid is None or len(self._packed) == 0:
            empty = np.array([], dtype=np.int32)
            return empty, empty, np.array([], dtype=np.bool_)

        sceneX, sceneY, inScene = self.getSceneCoords()

        # Initialize output arrays
        n = len(self._packed)
        screenX = np.zeros(n, dtype=np.int32)
        screenY = np.zeros(n, dtype=np.int32)
        visible = np.zeros(n, dtype=np.bool_)

        if not inScene.any():
            return screenX, screenY, visible

        # Get tile indices for in-scene tiles (clip to valid range)
        clippedX = sceneX.clip(0, grid.sizeX - 1)
        clippedY = sceneY.clip(0, grid.sizeY - 1)
        tileIdx = clippedX * grid.sizeY + clippedY

        # Get centers from grid cache
        centerX, centerY = grid.getTileCenters()
        screenX = centerX[tileIdx]
        screenY = centerY[tileIdx]

        # Visibility: in scene + valid tile + on screen
        tileValid = grid.tileValid[tileIdx]

        if margin == 0:
            onScreen = (
                (screenX >= grid.viewMinX)
                & (screenX < grid.viewMaxX)
                & (screenY >= grid.viewMinY)
                & (screenY < grid.viewMaxY)
            )
        else:
            onScreen = (
                (screenX >= grid.viewMinX - margin)
                & (screenX < grid.viewMaxX + margin)
                & (screenY >= grid.viewMinY - margin)
                & (screenY < grid.viewMaxY + margin)
            )

        visible = inScene & tileValid & onScreen

        return screenX, screenY, visible

    def getVisibleIndices(self, margin: int = 0) -> np.ndarray:
        """
        Get indices of path tiles visible on screen.

        Args:
            margin: Extra pixels around viewport

        Returns:
            Array of indices into the path where tiles are visible.

        Example:
            >>> indices = path.getVisibleIndices()
            >>> for i in indices:
            ...     pos = path.getPosition(i)
            ...     print(f"Visible: {pos}")
        """
        _, _, visible = self.getScreenCoords(margin=margin)
        return np.where(visible)[0]

    def getVisibleQuads(self) -> List["Quad"]:
        """
        Get Quads for all visible path tiles.

        Returns:
            List of Quad objects for tiles currently on screen.

        Example:
            >>> quads = path.getVisibleQuads()
            >>> for quad in quads:
            ...     quad.debug()  # Visualize on screen
        """
        grid = self._getTileGrid()
        if grid is None:
            return []

        sceneX, sceneY, inScene = self.getSceneCoords()
        indices = np.where(inScene)[0]

        quads = []
        for i in indices:
            sx, sy = sceneX[i], sceneY[i]
            tileIdx = sx * grid.sizeY + sy
            if grid.tileOnScreen[tileIdx]:
                quads.append(grid.getTileQuad(tileIdx))

        return quads

    def getScreenPoint(self, i: int) -> "Point | None":
        """
        Get screen Point for path tile at index.

        Args:
            i: Index into path

        Returns:
            Point or None if tile not in scene or not valid.
        """
        from shadowlib.types import Point

        grid = self._getTileGrid()
        if grid is None or i < 0 or i >= len(self._packed):
            return None

        sceneX = int(self.worldX[i]) - grid.baseX
        sceneY = int(self.worldY[i]) - grid.baseY

        if not (0 <= sceneX < grid.sizeX and 0 <= sceneY < grid.sizeY):
            return None

        tileIdx = sceneX * grid.sizeY + sceneY
        if not grid.tileValid[tileIdx]:
            return None

        centerX, centerY = grid.getTileCenters()
        return Point(int(centerX[tileIdx]), int(centerY[tileIdx]))

    def getQuad(self, i: int) -> "Quad | None":
        """
        Get Quad for path tile at index.

        Args:
            i: Index into path

        Returns:
            Quad or None if tile not in scene.
        """
        grid = self._getTileGrid()
        if grid is None or i < 0 or i >= len(self._packed):
            return None

        sceneX = int(self.worldX[i]) - grid.baseX
        sceneY = int(self.worldY[i]) - grid.baseY

        if not (0 <= sceneX < grid.sizeX and 0 <= sceneY < grid.sizeY):
            return None

        tileIdx = sceneX * grid.sizeY + sceneY
        return grid.getTileQuad(tileIdx)

    # -------------------------------------------------------------------------
    # Basic properties and iteration
    # -------------------------------------------------------------------------

    @property
    def obstacles(self) -> List[PathObstacle]:
        """Get all obstacles in path."""
        return self._obstacles

    def length(self) -> int:
        """Get path length in tiles."""
        return len(self._packed)

    def isEmpty(self) -> bool:
        """Check if path is empty."""
        return len(self._packed) == 0

    def getPosition(self, i: int) -> PackedPosition | None:
        """
        Get PackedPosition at index (for compatibility).

        Creates a PackedPosition object on-demand. For bulk operations,
        prefer using worldX/worldY arrays directly.

        Args:
            i: Index into path

        Returns:
            PackedPosition or None if out of bounds.
        """
        if i < 0 or i >= len(self._packed):
            return None
        return PackedPosition.fromPacked(int(self._packed[i]))

    def getStart(self) -> PackedPosition | None:
        """Get start position."""
        return self.getPosition(0)

    def getEnd(self) -> PackedPosition | None:
        """Get end position (destination)."""
        return self.getPosition(len(self._packed) - 1)

    def getNextTile(self, current: PackedPosition) -> PackedPosition | None:
        """
        Get next tile from current position.

        Args:
            current: Current position

        Returns:
            Next tile or None if at end
        """
        # Vectorized search
        matches = np.where(self._packed == current.packed)[0]
        if len(matches) == 0:
            return None
        idx = matches[0]
        if idx < len(self._packed) - 1:
            return PackedPosition.fromPacked(int(self._packed[idx + 1]))
        return None

    def getObstacleAt(self, position: PackedPosition) -> PathObstacle | None:
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
        walk_ticks = len(self._packed)
        obstacle_ticks = sum(obs.duration for obs in self._obstacles)
        return walk_ticks + obstacle_ticks

    def getTotalSeconds(self) -> float:
        """
        Get total estimated duration in seconds.

        Returns:
            Total seconds (ticks * 0.6)
        """
        return self.getTotalDuration() * 0.6

    # -------------------------------------------------------------------------
    # Distance calculations (vectorized)
    # -------------------------------------------------------------------------

    def distanceToTile(self, worldX: int, worldY: int) -> np.ndarray:
        """
        Calculate Chebyshev distance from each path tile to a point.

        Args:
            worldX: Target X coordinate
            worldY: Target Y coordinate

        Returns:
            Array of distances (same length as path)

        Example:
            >>> dist = path.distanceToTile(playerX, playerY)
            >>> closestIdx = dist.argmin()
            >>> print(f"Closest tile at index {closestIdx}")
        """
        dx = np.abs(self.worldX - worldX)
        dy = np.abs(self.worldY - worldY)
        return np.maximum(dx, dy)

    def findClosestTile(self, worldX: int, worldY: int) -> int:
        """
        Find index of path tile closest to a point.

        Args:
            worldX: Target X coordinate
            worldY: Target Y coordinate

        Returns:
            Index of closest tile, or -1 if path is empty.
        """
        if len(self._packed) == 0:
            return -1
        return int(self.distanceToTile(worldX, worldY).argmin())

    def sliceFrom(self, startIdx: int) -> "Path":
        """
        Create new Path starting from given index.

        Useful for getting remaining path after reaching a waypoint.

        Args:
            startIdx: Index to start from

        Returns:
            New Path with tiles from startIdx onwards.
        """
        if startIdx < 0 or startIdx >= len(self._packed):
            return Path(np.array([], dtype=np.int32), [])

        newPacked = self._packed[startIdx:]

        # Filter obstacles that are still ahead
        remainingPositions = set(newPacked.tolist())
        newObstacles = [obs for obs in self._obstacles if obs.origin.packed in remainingPositions]

        return Path(newPacked, newObstacles)

    # -------------------------------------------------------------------------
    # Python protocol support
    # -------------------------------------------------------------------------

    def __len__(self) -> int:
        """Support len() builtin."""
        return len(self._packed)

    def __iter__(self):
        """Iterate over PackedPosition objects (creates on-demand)."""
        for p in self._packed:
            yield PackedPosition.fromPacked(int(p))

    def __getitem__(self, index) -> PackedPosition:
        """Support indexing (creates PackedPosition on-demand)."""
        return PackedPosition.fromPacked(int(self._packed[index]))

    def __repr__(self) -> str:
        return (
            f"Path({len(self._packed)} tiles, {len(self._obstacles)} obstacles, "
            f"~{self.getTotalSeconds():.1f}s)"
        )
