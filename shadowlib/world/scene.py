"""Scene utilities for working with tiles in the loaded scene."""

from typing import TYPE_CHECKING, Tuple

import numpy as np

if TYPE_CHECKING:
    from shadowlib.types import Point, Quad
    from shadowlib.world.projection import TileGrid


class VisibleTiles:
    """
    Collection of visible tiles with numpy array access.

    All data comes from the cached TileGrid - no additional computation.
    """

    __slots__ = ("_grid", "_indices")

    def __init__(self, grid: "TileGrid", indices: np.ndarray):
        self._grid = grid
        self._indices = indices

    def __len__(self) -> int:
        return len(self._indices)

    @property
    def sceneX(self) -> np.ndarray:
        """Scene X coordinates of visible tiles."""
        return self._grid._sceneXs[self._indices]

    @property
    def sceneY(self) -> np.ndarray:
        """Scene Y coordinates of visible tiles."""
        return self._grid._sceneYs[self._indices]

    @property
    def worldX(self) -> np.ndarray:
        """World X coordinates of visible tiles."""
        return self._grid._sceneXs[self._indices].astype(np.int32) + self._grid.baseX

    @property
    def worldY(self) -> np.ndarray:
        """World Y coordinates of visible tiles."""
        return self._grid._sceneYs[self._indices].astype(np.int32) + self._grid.baseY

    @property
    def screenX(self) -> np.ndarray:
        """Screen X coordinates of tile centers."""
        centerX, _ = self._grid.getTileCenters()
        return centerX[self._indices]

    @property
    def screenY(self) -> np.ndarray:
        """Screen Y coordinates of tile centers."""
        _, centerY = self._grid.getTileCenters()
        return centerY[self._indices]

    @property
    def indices(self) -> np.ndarray:
        """Flat tile indices into the grid."""
        return self._indices

    def getScreenPoint(self, i: int) -> "Point":
        """Get screen position of tile at local index i."""
        from shadowlib.types import Point

        centerX, centerY = self._grid.getTileCenters()
        idx = self._indices[i]
        return Point(int(centerX[idx]), int(centerY[idx]))

    def getWorldCoord(self, i: int) -> Tuple[int, int]:
        """Get world coordinates of tile at local index i."""
        idx = self._indices[i]
        return (
            int(self._grid._sceneXs[idx]) + self._grid.baseX,
            int(self._grid._sceneYs[idx]) + self._grid.baseY,
        )

    def getQuad(self, i: int) -> "Quad":
        """Get Quad for tile at local index i."""
        return self._grid.getTileQuad(self._indices[i])


class Scene:
    """
    Utilities for working with tiles in the loaded scene.

    All methods use the cached TileGrid from Projection - no redundant computation.
    Cache is automatically invalidated when camera/scene/entity events arrive.

    Example:
        >>> from shadowlib.world.scene import scene
        >>>
        >>> visible = scene.getVisibleTiles()
        >>> if visible:
        ...     print(f"Found {len(visible)} visible tiles")
        ...     # Vectorized operations on numpy arrays
        ...     dist = np.abs(visible.worldX - 3100) + np.abs(visible.worldY - 3200)
        ...     closest = visible.getScreenPoint(np.argmin(dist))
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _getTileGrid(self) -> "TileGrid | None":
        """Get cached TileGrid from projection singleton."""
        from shadowlib.world.projection import projection

        return projection.tiles

    def _getPlayerScenePos(self) -> Tuple[int, int] | None:
        """Get player scene position from cache."""
        from shadowlib.globals import getEventCache

        gt = getEventCache().getGametickState()
        if not gt:
            return None
        x, y = gt.get("sceneX"), gt.get("sceneY")
        return (x, y) if x is not None and y is not None else None

    def getVisibleTiles(self, margin: int = 0) -> VisibleTiles | None:
        """
        Get all tiles visible on screen.

        Args:
            margin: Extra pixels around viewport to include

        Returns:
            VisibleTiles or None if not ready
        """
        grid = self._getTileGrid()
        if grid is None:
            return None

        indices = grid.getVisibleIndices(margin=margin)
        return VisibleTiles(grid, indices)

    def getVisibleTilesNearPlayer(self, radius: int = 25, margin: int = 0) -> VisibleTiles | None:
        """
        Get visible tiles within radius of player.

        Args:
            radius: Tile radius around player
            margin: Extra pixels around viewport to include

        Returns:
            VisibleTiles or None if not ready
        """
        grid = self._getTileGrid()
        if grid is None:
            return None

        pos = self._getPlayerScenePos()
        if pos is None:
            return None

        px, py = pos

        # Create mask for tiles near player
        nearMask = (
            (grid._sceneXs >= max(0, px - radius))
            & (grid._sceneXs <= min(grid.sizeX - 1, px + radius))
            & (grid._sceneYs >= max(0, py - radius))
            & (grid._sceneYs <= min(grid.sizeY - 1, py + radius))
        )

        indices = grid.getVisibleIndices(mask=nearMask, margin=margin)
        return VisibleTiles(grid, indices)

    def getTilesInArea(
        self,
        worldX1: int,
        worldY1: int,
        worldX2: int,
        worldY2: int,
        margin: int = 0,
    ) -> VisibleTiles | None:
        """
        Get visible tiles in a world rectangle.

        Args:
            worldX1, worldY1: First corner
            worldX2, worldY2: Second corner
            margin: Extra pixels around viewport

        Returns:
            VisibleTiles or None if not ready or area outside scene
        """
        grid = self._getTileGrid()
        if grid is None:
            return None

        # Convert to scene coords
        minSX = max(0, min(worldX1, worldX2) - grid.baseX)
        maxSX = min(grid.sizeX - 1, max(worldX1, worldX2) - grid.baseX)
        minSY = max(0, min(worldY1, worldY2) - grid.baseY)
        maxSY = min(grid.sizeY - 1, max(worldY1, worldY2) - grid.baseY)

        if minSX > maxSX or minSY > maxSY:
            return None

        # Create mask
        areaMask = (
            (grid._sceneXs >= minSX)
            & (grid._sceneXs <= maxSX)
            & (grid._sceneYs >= minSY)
            & (grid._sceneYs <= maxSY)
        )

        indices = grid.getVisibleIndices(mask=areaMask, margin=margin)
        return VisibleTiles(grid, indices)

    def isTileOnScreen(self, worldX: int, worldY: int) -> bool:
        """Check if a world tile is visible on screen."""
        grid = self._getTileGrid()
        if grid is None:
            return False

        sceneX = worldX - grid.baseX
        sceneY = worldY - grid.baseY
        if not (0 <= sceneX < grid.sizeX and 0 <= sceneY < grid.sizeY):
            return False

        tileIdx = sceneX * grid.sizeY + sceneY
        return bool(grid.tileOnScreen[tileIdx])

    def getTileQuad(self, worldX: int, worldY: int) -> "Quad | None":
        """Get Quad for a world tile. Returns None if not in scene or not valid."""
        grid = self._getTileGrid()
        if grid is None:
            return None

        sceneX = worldX - grid.baseX
        sceneY = worldY - grid.baseY
        if not (0 <= sceneX < grid.sizeX and 0 <= sceneY < grid.sizeY):
            return None

        tileIdx = sceneX * grid.sizeY + sceneY
        if not grid.tileValid[tileIdx]:
            return None

        return grid.getTileQuad(tileIdx)

    def getSceneBounds(self) -> Tuple[int, int, int, int]:
        """Get world bounds: (minX, minY, maxX, maxY)."""
        grid = self._getTileGrid()
        if grid is None:
            from shadowlib.world.projection import projection

            return (
                projection.baseX,
                projection.baseY,
                projection.baseX + projection.sizeX - 1,
                projection.baseY + projection.sizeY - 1,
            )
        return (grid.baseX, grid.baseY, grid.baseX + grid.sizeX - 1, grid.baseY + grid.sizeY - 1)

    def isInScene(self, worldX: int, worldY: int) -> bool:
        """Check if world coordinate is in loaded scene."""
        grid = self._getTileGrid()
        if grid is None:
            return False
        sceneX = worldX - grid.baseX
        sceneY = worldY - grid.baseY
        return 0 <= sceneX < grid.sizeX and 0 <= sceneY < grid.sizeY


# Module-level singleton
scene = Scene()
