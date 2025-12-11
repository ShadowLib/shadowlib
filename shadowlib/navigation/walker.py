"""
Walker module - handles walking from point A to point B.

Smart walker that:
1. Gets a path from the pathfinder
2. Tracks current walk target to avoid spam-clicking
3. Only clicks new tiles when near current target or idle
4. Finds suitable visible tiles along the path
"""

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from shadowlib.types import Quad
    from shadowlib.types.path import Path

# Local coordinate units per tile (RuneLite LocalPoint)
LOCAL_UNITS_PER_TILE = 128


class Walker:
    """
    Singleton walker for navigating from point A to point B.

    Uses pathfinder to get a path, then clicks visible tiles to walk.
    Tracks current walk target to avoid spam-clicking - only clicks
    new tiles when the player is near their current target or idle.

    Example:
        from shadowlib.navigation.walker import walker

        # Walk to destination (handles target tracking automatically)
        while walker.distanceToDestination(3165, 3487) > 0:
            walker.walkTo(3165, 3487)
            time.sleep(0.6)

        # Or via client namespace
        from shadowlib.client import client
        client.navigation.walker.walkTo(3165, 3487)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """Actual initialization, runs once."""
        pass

    def _getPlayerPosition(self) -> tuple[int, int, int] | None:
        """Get player world position (x, y, plane) from cache."""
        from shadowlib.client import client

        pos = client.cache.position
        if pos is None:
            return None
        return (pos.get("x", 0), pos.get("y", 0), pos.get("plane", 0))

    def _getPlayerScenePosition(self) -> tuple[int, int] | None:
        """Get player scene position (sceneX, sceneY) from cache."""
        from shadowlib.client import client

        pos = client.cache.scenePosition
        if pos is None:
            return None
        return (pos.get("sceneX", 0), pos.get("sceneY", 0))

    def _getTargetScenePosition(self) -> tuple[int, int] | None:
        """
        Get current walk target in scene coordinates.

        The target_location from Java is in LOCAL coordinates (128 units/tile).
        Converts to scene coordinates for distance calculations.

        Returns:
            Tuple of (sceneX, sceneY) or None if not walking to a target.
        """
        from shadowlib.client import client

        target = client.cache.targetLocation
        if target is None:
            return None

        localX = target.get("x")
        localY = target.get("y")
        if localX is None or localY is None:
            return None

        # Convert local to scene coords (128 local units = 1 tile)
        sceneX = localX // LOCAL_UNITS_PER_TILE
        sceneY = localY // LOCAL_UNITS_PER_TILE

        return (sceneX, sceneY)

    def _distanceToTarget(self) -> int | None:
        """
        Get Chebyshev distance from player to current walk target.

        Returns:
            Distance in tiles, or None if no target or position unknown.
        """
        playerPos = self._getPlayerScenePosition()
        targetPos = self._getTargetScenePosition()

        if playerPos is None or targetPos is None:
            return None

        playerX, playerY = playerPos
        targetX, targetY = targetPos

        return max(abs(targetX - playerX), abs(targetY - playerY))

    def hasTarget(self) -> bool:
        """
        Check if player currently has a walk target.

        Returns:
            True if player is walking to a target.
        """
        return self._getTargetScenePosition() is not None

    def isNearTarget(self, threshold: int = 2) -> bool:
        """
        Check if player is near their current walk target.

        Args:
            threshold: Distance in tiles to consider "near" (default 2)

        Returns:
            True if player is within threshold of target, or has no target.
        """
        dist = self._distanceToTarget()
        if dist is None:
            return True  # No target = effectively "at" target

        return dist <= threshold

    def shouldClickNewTile(self, threshold: int = 2) -> bool:
        """
        Determine if we should click a new tile to continue walking.

        Returns True if:
        - Player has no current walk target (idle)
        - Player is within threshold tiles of current target

        Args:
            threshold: Distance threshold to consider "near target" (default 2)

        Returns:
            True if we should click a new tile.
        """
        return self.isNearTarget(threshold=threshold)

    def _findFirstObstacleIndex(self, path: "Path") -> int:
        """
        Find the index of the first obstacle on the path.

        Args:
            path: Path to search

        Returns:
            Index of first obstacle origin, or path length if no obstacles
        """
        if not path.hasObstacles():
            return path.length()

        # Find the earliest obstacle origin
        firstObstacleIdx = path.length()
        for obstacle in path.obstacles:
            # Find where this obstacle's origin is on the path
            matches = np.where(path.packed == obstacle.origin.packed)[0]
            if len(matches) > 0:
                idx = int(matches[0])
                if idx < firstObstacleIdx:
                    firstObstacleIdx = idx

        return firstObstacleIdx

    def _selectWalkTile(
        self,
        path: "Path",
        visibleIndices: np.ndarray,
        playerX: int,
        playerY: int,
        maxIndex: int,
    ) -> int | None:
        """
        Select the optimal tile to click for walking.

        Selection criteria:
        - Must be in visibleIndices
        - Must be before maxIndex (obstacle)
        - Quad center must be inside viewport (clickable)
        - Prefers tiles further from player (more efficient walking)
        - Skips tiles too close to player (< 3 tiles)

        Args:
            path: The path to walk
            visibleIndices: Indices of visible path tiles
            playerX: Player world X
            playerY: Player world Y
            maxIndex: Maximum index (first obstacle or path end)

        Returns:
            Best tile index to click, or None if no suitable tile
        """
        from shadowlib.world.scene import scene

        # Filter to tiles before obstacle
        validIndices = visibleIndices[visibleIndices < maxIndex]

        if len(validIndices) == 0:
            return None

        # Get tile grid for viewport bounds
        grid = scene._getTileGrid()
        if grid is None:
            return None

        # Filter to tiles whose quad is FULLY inside viewport (all 4 corners)
        clickableIndices = []
        for idx in validIndices:
            quad = path.getQuad(int(idx))
            if quad is not None:
                # Check all 4 vertices are inside viewport
                allInside = all(
                    grid.viewMinX <= p.x <= grid.viewMaxX and grid.viewMinY <= p.y <= grid.viewMaxY
                    for p in quad.vertices
                )
                if allInside:
                    clickableIndices.append(int(idx))

        if len(clickableIndices) == 0:
            return None

        clickableIndices = np.array(clickableIndices)

        # Get world coordinates for clickable tiles
        worldX = path.worldX[clickableIndices]
        worldY = path.worldY[clickableIndices]

        # Calculate distance from player (Chebyshev)
        dist = np.maximum(np.abs(worldX - playerX), np.abs(worldY - playerY))

        # Filter out tiles too close (< 3 tiles away)
        farEnough = dist >= 3
        if not farEnough.any():
            # If all tiles are close, just pick the furthest
            bestLocal = int(np.argmax(dist))
            return int(clickableIndices[bestLocal])

        # Among far enough tiles, pick the one furthest along the path
        # (which is the highest index in clickableIndices)
        farMask = np.array(farEnough)
        farIndices = clickableIndices[farMask]
        return int(farIndices[-1])  # Last one is furthest along path

    def clickTile(self, worldX: int, worldY: int) -> bool:
        """
        Click a specific world tile to walk to it.

        Hovers over the tile, waits for WALK action, and clicks.

        Args:
            worldX: World X coordinate
            worldY: World Y coordinate

        Returns:
            True if tile was clicked successfully, False otherwise

        Example:
            >>> walker.clickTile(3165, 3487)
        """
        from shadowlib.client import client
        from shadowlib.world.scene import scene

        # Get the quad for this tile
        quad = scene.getTileQuad(worldX, worldY)
        if quad is None:
            return False

        # Hover on the tile
        quad.hover()

        # Wait for WALK action to appear in menu
        if not client.interactions.menu.waitHasType("WALK", timeout=0.5):
            return False

        # Click the walk action
        return client.interactions.menu.clickOptionType("WALK")

    def walkTo(
        self,
        destX: int,
        destY: int,
        destPlane: int = 0,
        margin: int = 50,
        nearTargetThreshold: int = 2,
    ) -> bool:
        """
        Walk towards destination by clicking a tile along the path.

        Smart walking with target tracking:
        - Only clicks a new tile if player is near current target or idle
        - Avoids spam-clicking while player is still walking
        - Automatically selects optimal visible tile along path

        Currently walks up to the first obstacle only - obstacles like doors,
        ladders, etc. need separate handling.

        Args:
            destX: Destination world X coordinate
            destY: Destination world Y coordinate
            destPlane: Destination plane (default 0)
            margin: Pixel margin from viewport edge for tile selection (default 50)
            nearTargetThreshold: Distance to target before clicking new tile (default 2)

        Returns:
            True if a tile was clicked or already walking, False on error

        Example:
            >>> from shadowlib.navigation.walker import walker
            >>> import time
            >>>
            >>> # Walk to destination with automatic target tracking
            >>> while walker.distanceToDestination(3165, 3487) > 0:
            ...     walker.walkTo(3165, 3487)
            ...     time.sleep(0.6)  # Check every tick
            >>> print("Arrived!")
        """
        from shadowlib.navigation.pathfinder import pathfinder

        # Get player position
        playerPos = self._getPlayerPosition()
        if playerPos is None:
            return False

        playerX, playerY, playerPlane = playerPos

        # Check if already at destination
        if playerX == destX and playerY == destY and playerPlane == destPlane:
            return True  # Already there

        # Check if we should click a new tile or wait
        if not self.shouldClickNewTile(threshold=nearTargetThreshold):
            # Still walking to current target, no need to click
            return True  # Return True because we're making progress

        # Get path to destination
        path = pathfinder.getPath(destX, destY, destPlane)
        if path is None or path.isEmpty():
            return False

        # Find first obstacle (we'll walk up to it)
        obstacleIdx = self._findFirstObstacleIndex(path)

        # Get visible path tiles (with margin to avoid edge clicks)
        visibleIndices = path.getVisibleIndices(margin=margin)

        if len(visibleIndices) == 0:
            # No visible path tiles - might need to turn camera or wait
            return False

        # Select optimal tile to click
        targetIdx = self._selectWalkTile(path, visibleIndices, playerX, playerY, obstacleIdx)

        if targetIdx is None:
            return False

        # Get the quad for this tile
        quad = path.getQuad(targetIdx)
        if quad is None:
            return False

        # Click the tile
        return self._clickWalkQuad(quad)

    def _clickWalkQuad(self, quad: "Quad") -> bool:
        """
        Hover over quad and click with WALK action.

        Args:
            quad: Quad to click

        Returns:
            True if clicked successfully
        """
        from shadowlib.client import client

        # Hover on the tile
        quad.hover()

        # Wait for WALK action to appear in menu
        if not client.interactions.menu.waitHasType("WALK", timeout=0.5):
            return False

        # Click the walk action
        return client.interactions.menu.clickOptionType("WALK")

    def isMoving(self) -> bool:
        """
        Check if player is currently moving.

        Returns True if player has a walk target they haven't reached yet.

        Returns:
            True if player is moving

        Example:
            >>> while walker.isMoving():
            ...     time.sleep(0.1)
            >>> print("Stopped moving")
        """
        return self.hasTarget()

    def distanceToDestination(self, destX: int, destY: int) -> int:
        """
        Get Chebyshev distance from player to destination.

        Args:
            destX: Destination world X
            destY: Destination world Y

        Returns:
            Distance in tiles, or -1 if position unknown
        """
        playerPos = self._getPlayerPosition()
        if playerPos is None:
            return -1

        playerX, playerY, _ = playerPos
        return max(abs(destX - playerX), abs(destY - playerY))


# Module-level singleton instance
walker = Walker()
