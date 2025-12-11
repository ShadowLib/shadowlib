"""Projection utilities for converting local coordinates to screen coordinates."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from shadowlib.types.point import Point

if TYPE_CHECKING:
    from shadowlib.types import Quad


@dataclass
class CameraState:
    """Per-frame camera state."""

    cameraX: float
    cameraY: float
    cameraZ: float
    cameraPitch: float  # radians
    cameraYaw: float  # radians
    scale: int


@dataclass
class EntityTransform:
    """Per-frame entity transform data (for WorldEntity instances)."""

    entityX: int
    entityY: int
    orientation: int  # 0-2047 JAU
    groundHeight: int


@dataclass
class EntityConfig:
    """Static WorldEntity config - set once on WorldView load."""

    boundsX: int
    boundsY: int
    boundsWidth: int
    boundsHeight: int

    @property
    def centerX(self) -> int:
        return (self.boundsX + self.boundsWidth // 2) * 128

    @property
    def centerY(self) -> int:
        return (self.boundsY + self.boundsHeight // 2) * 128


class TileGrid:
    """
    Cached projection of all tile corners in the scene.

    Projects (sizeX+1) x (sizeY+1) corner vertices. Tile (x,y) has corners:
    - NW: corner[x, y]
    - NE: corner[x+1, y]
    - SE: corner[x+1, y+1]
    - SW: corner[x, y+1]

    All data stored as flat arrays indexed by: x * (sizeY+1) + y for corners,
    or x * sizeY + y for tiles.
    """

    __slots__ = (
        "cornerX",
        "cornerY",
        "cornerValid",
        "sizeX",
        "sizeY",
        "baseX",
        "baseY",
        "plane",
        "viewMinX",
        "viewMaxX",
        "viewMinY",
        "viewMaxY",
        "_sceneXs",
        "_sceneYs",
        "_tileValid",
        "_tileOnScreen",
    )

    def __init__(
        self,
        cornerX: np.ndarray,
        cornerY: np.ndarray,
        cornerValid: np.ndarray,
        sizeX: int,
        sizeY: int,
        baseX: int,
        baseY: int,
        plane: int,
        viewMinX: int,
        viewMaxX: int,
        viewMinY: int,
        viewMaxY: int,
    ):
        self.cornerX = cornerX  # int32[(sizeX+1)*(sizeY+1)]
        self.cornerY = cornerY  # int32[(sizeX+1)*(sizeY+1)]
        self.cornerValid = cornerValid  # bool[(sizeX+1)*(sizeY+1)]
        self.sizeX = sizeX
        self.sizeY = sizeY
        self.baseX = baseX
        self.baseY = baseY
        self.plane = plane
        self.viewMinX = viewMinX
        self.viewMaxX = viewMaxX
        self.viewMinY = viewMinY
        self.viewMaxY = viewMaxY

        # Pre-compute tile scene coordinates (used for filtering)
        tileCount = sizeX * sizeY
        self._sceneXs = (np.arange(tileCount, dtype=np.int32) // sizeY).astype(np.int16)
        self._sceneYs = (np.arange(tileCount, dtype=np.int32) % sizeY).astype(np.int16)

        # Pre-compute tile validity and visibility (lazy, computed on first access)
        self._tileValid: np.ndarray | None = None
        self._tileOnScreen: np.ndarray | None = None

    def _cornerIdx(self, x: int, y: int) -> int:
        """Get flat index for corner at (x, y)."""
        return x * (self.sizeY + 1) + y

    def _tileIdx(self, x: int, y: int) -> int:
        """Get flat index for tile at (x, y)."""
        return x * self.sizeY + y

    @property
    def tileValid(self) -> np.ndarray:
        """Bool array of tile validity (all 4 corners valid). Shape: [sizeX * sizeY]."""
        if self._tileValid is None:
            sy1 = self.sizeY + 1
            # Get corner indices for all tiles
            tileIdxs = np.arange(self.sizeX * self.sizeY, dtype=np.int32)
            tx = tileIdxs // self.sizeY
            ty = tileIdxs % self.sizeY
            # Corner indices: NW, NE, SE, SW
            nw = tx * sy1 + ty
            ne = (tx + 1) * sy1 + ty
            se = (tx + 1) * sy1 + (ty + 1)
            sw = tx * sy1 + (ty + 1)
            self._tileValid = (
                self.cornerValid[nw]
                & self.cornerValid[ne]
                & self.cornerValid[se]
                & self.cornerValid[sw]
            )
        return self._tileValid

    @property
    def tileOnScreen(self) -> np.ndarray:
        """Bool array of tiles with center on screen. Shape: [sizeX * sizeY]."""
        if self._tileOnScreen is None:
            # Compute tile centers from corners
            centerX, centerY = self.getTileCenters()
            self._tileOnScreen = (
                self.tileValid
                & (centerX >= self.viewMinX)
                & (centerX < self.viewMaxX)
                & (centerY >= self.viewMinY)
                & (centerY < self.viewMaxY)
            )
        return self._tileOnScreen

    def getTileCenters(self) -> tuple[np.ndarray, np.ndarray]:
        """Get screen coordinates of tile centers. Returns (centerX, centerY) arrays."""
        sy1 = self.sizeY + 1
        tileIdxs = np.arange(self.sizeX * self.sizeY, dtype=np.int32)
        tx = tileIdxs // self.sizeY
        ty = tileIdxs % self.sizeY
        nw = tx * sy1 + ty
        ne = (tx + 1) * sy1 + ty
        se = (tx + 1) * sy1 + (ty + 1)
        sw = tx * sy1 + (ty + 1)
        centerX = (self.cornerX[nw] + self.cornerX[ne] + self.cornerX[se] + self.cornerX[sw]) >> 2
        centerY = (self.cornerY[nw] + self.cornerY[ne] + self.cornerY[se] + self.cornerY[sw]) >> 2
        return centerX, centerY

    def getTileCorners(self, tileIdx: int) -> tuple[int, int, int, int, int, int, int, int]:
        """Get screen coords of tile corners: (nwX, nwY, neX, neY, seX, seY, swX, swY)."""
        tx = tileIdx // self.sizeY
        ty = tileIdx % self.sizeY
        sy1 = self.sizeY + 1
        nw = tx * sy1 + ty
        ne = (tx + 1) * sy1 + ty
        se = (tx + 1) * sy1 + (ty + 1)
        sw = tx * sy1 + (ty + 1)
        return (
            int(self.cornerX[nw]),
            int(self.cornerY[nw]),
            int(self.cornerX[ne]),
            int(self.cornerY[ne]),
            int(self.cornerX[se]),
            int(self.cornerY[se]),
            int(self.cornerX[sw]),
            int(self.cornerY[sw]),
        )

    def getTileQuad(self, tileIdx: int) -> "Quad":
        """Get Quad for tile at flat index."""
        from shadowlib.types import Quad

        nwX, nwY, neX, neY, seX, seY, swX, swY = self.getTileCorners(tileIdx)
        return Quad.fromCoords([(nwX, nwY), (neX, neY), (seX, seY), (swX, swY)])

    def getVisibleIndices(self, mask: np.ndarray | None = None, margin: int = 0) -> np.ndarray:
        """
        Get flat indices of visible tiles, optionally filtered by mask.

        Args:
            mask: Optional bool array [sizeX * sizeY] to filter tiles
            margin: Extra pixels around viewport to include
        """
        if margin == 0:
            visible = self.tileOnScreen
        else:
            centerX, centerY = self.getTileCenters()
            visible = (
                self.tileValid
                & (centerX >= self.viewMinX - margin)
                & (centerX < self.viewMaxX + margin)
                & (centerY >= self.viewMinY - margin)
                & (centerY < self.viewMaxY + margin)
            )

        if mask is not None:
            visible = visible & mask

        return np.where(visible)[0]


class Projection:
    """
    Fast projection from local coordinates to canvas coordinates.

    Singleton that caches tile projections. Cache is invalidated by StateBuilder
    when camera_changed, world_entity, or world_view_loaded events arrive.

    Access cached tiles via the `tiles` property which returns a TileGrid.
    """

    LOCAL_COORD_BITS = 7
    LOCAL_TILE_SIZE = 128

    VIEWPORT_WIDTH = 512
    VIEWPORT_HEIGHT = 334
    VIEWPORT_X_OFFSET = 4
    VIEWPORT_Y_OFFSET = 4

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        # Sin/cos lookup tables (JAU: 0-2047)
        unit = np.pi / 1024
        angles = np.arange(2048) * unit
        self._sinTable = np.sin(angles).astype(np.float32)
        self._cosTable = np.cos(angles).astype(np.float32)

        # Scene data
        self.tileHeights: np.ndarray | None = None
        self.bridgeFlags: np.ndarray | None = None
        self.baseX: int = 0
        self.baseY: int = 0
        self.sizeX: int = 104
        self.sizeY: int = 104
        self.entityConfig: EntityConfig | None = None

        # Camera trig (updated on refresh)
        self._camX: float = 0
        self._camY: float = 0
        self._camZ: float = 0
        self._scale: int = 512
        self._pitchSin: float = 0
        self._pitchCos: float = 1
        self._yawSin: float = 0
        self._yawCos: float = 1

        # Entity transform
        self._entityX: int = 0
        self._entityY: int = 0
        self._orientSin: float = 0
        self._orientCos: float = 1
        self._groundHeight: int = 0
        self._centerX: int = 0
        self._centerY: int = 0

        # Tile cache
        self._tileGrid: TileGrid | None = None
        self._stale: bool = True

    # -------------------------------------------------------------------------
    # Cache access
    # -------------------------------------------------------------------------

    def invalidate(self):
        """Mark cache as stale. Called by StateBuilder on relevant events."""
        self._stale = True

    @property
    def tiles(self) -> TileGrid | None:
        """
        Get cached tile projections. Recomputes if stale.

        Returns TileGrid with all corner projections, or None if not ready.
        """
        if not self._stale and self._tileGrid is not None:
            return self._tileGrid

        if not self._refreshCamera():
            return None

        if self.tileHeights is None:
            return None

        self._computeTileGrid()
        return self._tileGrid

    def _refreshCamera(self) -> bool:
        """Load camera state from EventCache. Returns True if successful."""
        from shadowlib.globals import getEventCache

        cache = getEventCache()
        camData = cache.getCameraState()
        if not camData:
            return False

        self._camX, self._camY, self._camZ = camData[0], camData[1], camData[2]
        pitch, yaw, self._scale = camData[3], camData[4], camData[5]
        self._pitchSin = np.sin(pitch)
        self._pitchCos = np.cos(pitch)
        self._yawSin = np.sin(yaw)
        self._yawCos = np.cos(yaw)

        # Entity transform
        entData = cache.getEntityTransform()
        if entData:
            self._entityX, self._entityY = entData[0], entData[1]
            self._orientSin = self._sinTable[entData[2]]
            self._orientCos = self._cosTable[entData[2]]
            self._groundHeight = entData[3]
        else:
            self._entityX = self._entityY = self._groundHeight = 0
            self._orientSin, self._orientCos = 0.0, 1.0

        return True

    def _computeTileGrid(self):
        """Compute corner projections for all tiles."""
        # Get current plane
        from shadowlib.globals import getEventCache

        gametick = getEventCache().getGametickState()
        plane = gametick.get("plane", 0) if gametick else 0

        # Generate corner grid: (sizeX+1) x (sizeY+1)
        cx = np.arange(self.sizeX + 1, dtype=np.int32)
        cy = np.arange(self.sizeY + 1, dtype=np.int32)
        gridX, gridY = np.meshgrid(cx, cy, indexing="ij")

        # Local coords for corners (not +64 for centers)
        localX = (gridX << 7).ravel().astype(np.float32)
        localY = (gridY << 7).ravel().astype(np.float32)

        # Project
        screenX, screenY, valid = self._projectBatch(localX, localY, plane)

        self._tileGrid = TileGrid(
            cornerX=screenX.astype(np.int32),
            cornerY=screenY.astype(np.int32),
            cornerValid=valid,
            sizeX=self.sizeX,
            sizeY=self.sizeY,
            baseX=self.baseX,
            baseY=self.baseY,
            plane=plane,
            viewMinX=self.VIEWPORT_X_OFFSET,
            viewMaxX=self.VIEWPORT_X_OFFSET + self.VIEWPORT_WIDTH,
            viewMinY=self.VIEWPORT_Y_OFFSET,
            viewMaxY=self.VIEWPORT_Y_OFFSET + self.VIEWPORT_HEIGHT,
        )
        self._stale = False

    def _projectBatch(
        self, localX: np.ndarray, localY: np.ndarray, plane: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Core projection: local coords -> screen coords."""
        # Tile heights with bridge correction
        sceneX = (localX.astype(np.int32) >> 7).clip(0, self.sizeX - 1)
        sceneY = (localY.astype(np.int32) >> 7).clip(0, self.sizeY - 1)
        tilePlane = np.where((plane < 3) & self.bridgeFlags[sceneX, sceneY], plane + 1, plane)
        z = self.tileHeights[tilePlane, sceneX, sceneY].astype(np.float32) + self._groundHeight

        # Entity transform (identity if top-level)
        if self.entityConfig is None:
            worldX, worldY = localX, localY
        else:
            cx = localX - self._centerX
            cy = localY - self._centerY
            worldX = self._entityX + cy * self._orientSin + cx * self._orientCos
            worldY = self._entityY + cy * self._orientCos - cx * self._orientSin

        # Camera-relative
        dx = worldX - self._camX
        dy = worldY - self._camY
        dz = z - self._camZ

        # Rotate by yaw and pitch
        x1 = dx * self._yawCos + dy * self._yawSin
        y1 = dy * self._yawCos - dx * self._yawSin
        y2 = dz * self._pitchCos - y1 * self._pitchSin
        depth = y1 * self._pitchCos + dz * self._pitchSin

        # Project
        valid = depth >= 50
        safeDepth = np.where(valid, depth, 1.0)
        screenX = (self.VIEWPORT_WIDTH / 2 + x1 * self._scale / safeDepth).astype(np.int32)
        screenY = (self.VIEWPORT_HEIGHT / 2 + y2 * self._scale / safeDepth).astype(np.int32)
        screenX += self.VIEWPORT_X_OFFSET
        screenY += self.VIEWPORT_Y_OFFSET

        return screenX, screenY, valid

    # -------------------------------------------------------------------------
    # Scene data (set by StateBuilder)
    # -------------------------------------------------------------------------

    def setScene(
        self,
        tileHeights: np.ndarray,
        bridgeFlags: np.ndarray,
        baseX: int,
        baseY: int,
        sizeX: int,
        sizeY: int,
    ):
        """Set scene data on WorldView load."""
        self.tileHeights = tileHeights.astype(np.int32)
        self.bridgeFlags = bridgeFlags.astype(np.bool_)
        self.baseX = baseX
        self.baseY = baseY
        self.sizeX = sizeX
        self.sizeY = sizeY

    def setEntityConfig(self, config: EntityConfig | None):
        """Set WorldEntity config. None for top-level world."""
        self.entityConfig = config
        if config:
            self._centerX = config.centerX
            self._centerY = config.centerY
        else:
            self._centerX = self._centerY = 0

    # -------------------------------------------------------------------------
    # Single-point convenience (uses cache when possible)
    # -------------------------------------------------------------------------

    def worldTileToCanvas(self, worldX: int, worldY: int, plane: int) -> Point | None:
        """Project a world tile center to screen. Returns None if off-scene or behind camera."""
        grid = self.tiles
        if grid is None or grid.plane != plane:
            return None

        sceneX = worldX - self.baseX
        sceneY = worldY - self.baseY
        if not (0 <= sceneX < self.sizeX and 0 <= sceneY < self.sizeY):
            return None

        tileIdx = sceneX * self.sizeY + sceneY
        if not grid.tileValid[tileIdx]:
            return None

        centerX, centerY = grid.getTileCenters()
        return Point(int(centerX[tileIdx]), int(centerY[tileIdx]))


# Module-level singleton
projection = Projection()
