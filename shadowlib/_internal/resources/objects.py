"""
Game Objects resource manager.

Handles downloading and querying OSRS object definitions and locations
from the cache dump SQLite database.

Positions are stored as packed 32-bit integers:
- Bits [31-30]: Plane (2 bits, 0-3)
- Bits [29-15]: X coordinate (15 bits, 0-32767)
- Bits [14-0]: Y coordinate (15 bits, 0-32767)
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from ..utils.packed_position import pack_position_signed, unpack_position
from .base import BaseResource


class ObjectsResource(BaseResource):
    """
    Manages OSRS object data with automatic version checking and updates.

    Provides access to object definitions, names, locations, and properties
    from the game cache dump SQLite database.
    """

    def __init__(self):
        # Share metadata with varps (same source directory)
        super().__init__("objects", shared_metadata_with="varps")
        self._db_connection = None
        # Override base URL - objects are stored in varps directory
        from .base import BASE_URL

        self.base_url = f"{BASE_URL}/varps/latest"

    def getRemoteFiles(self) -> Dict[str, str]:
        """Specify which files to download."""
        return {
            "objects.db": "objects.db.gz",  # Will be decompressed automatically
        }

    def _downloadAll(self) -> bool:
        """
        Download all resource files including shared metadata/varps to correct locations.

        Objects DB goes to objects directory, metadata/varps go to varps directory.
        """
        success = True

        # Download objects.db to objects directory
        url = f"{self.base_url}/objects.db.gz"
        dest = self.cache_dir / "objects.db"
        if not self._downloadFile(url, dest, decompress_gz=True):
            success = False

        # Download metadata.json to varps directory (shared metadata location)
        metadata_url = f"{self.base_url}/metadata.json"
        metadata_dest = self.metadata_cache_dir / "metadata.json"
        self.metadata_cache_dir.mkdir(parents=True, exist_ok=True)
        if not self._downloadFile(metadata_url, metadata_dest, decompress_gz=False):
            success = False

        # Download varps.json to varps directory
        varps_url = f"{self.base_url}/varps.json"
        varps_dest = self.metadata_cache_dir / "varps.json"
        if not self._downloadFile(varps_url, varps_dest, decompress_gz=False):
            success = False

        # Download varbits.json to varps directory
        varbits_url = f"{self.base_url}/varbits.json"
        varbits_dest = self.metadata_cache_dir / "varbits.json"
        if not self._downloadFile(varbits_url, varbits_dest, decompress_gz=False):
            success = False

        return success

    def _loadDataFiles(self):
        """Open database connection."""
        try:
            db_file = self.cache_dir / "objects.db"
            if not db_file.exists():
                raise FileNotFoundError(f"Objects database not found at {db_file}")

            # Close existing connection if any
            if self._db_connection:
                self._db_connection.close()

            # Open new connection
            self._db_connection = sqlite3.connect(str(db_file))
            self._db_connection.row_factory = sqlite3.Row  # Enable column access by name

            print("✅ Loaded objects database")

        except Exception as e:
            print(f"❌ Failed to load objects database: {e}")
            raise

    def _ensureConnection(self):
        """Ensure database is loaded and connected."""
        self.ensureLoaded()
        if self._db_connection is None:
            raise RuntimeError("Objects database connection not established")

    def getById(self, object_id: int) -> Optional[Dict[str, Any]]:
        """
        Get object definition by ID.

        Args:
            object_id: The object ID

        Returns:
            Dict with object name and ID, or None if not found

        Example:
            >>> objects.getById(1276)
            {'id': 1276, 'name': 'Tree'}
        """
        self._ensureConnection()

        cursor = self._db_connection.cursor()
        cursor.execute(
            """
            SELECT DISTINCT o.object_id, n.name
            FROM objects o
            JOIN names n ON o.name_id = n.id
            WHERE o.object_id = ?
            LIMIT 1
        """,
            (object_id,),
        )

        row = cursor.fetchone()
        if row:
            return {"id": row[0], "name": row[1]}
        return None

    def getByName(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """
        Search for objects by name.

        Args:
            name: Object name to search for
            exact: If True, match exact name; if False, match substring

        Returns:
            List of matching object definitions

        Example:
            >>> objects.getByName("tree")
            [{'id': 1276, 'name': 'Tree'}, {'id': 1277, 'name': 'Oak tree'}, ...]
        """
        self._ensureConnection()

        cursor = self._db_connection.cursor()
        if exact:
            cursor.execute(
                """
                SELECT DISTINCT o.object_id, n.name
                FROM objects o
                JOIN names n ON o.name_id = n.id
                WHERE n.name = ?
            """,
                (name,),
            )
        else:
            cursor.execute(
                """
                SELECT DISTINCT o.object_id, n.name
                FROM objects o
                JOIN names n ON o.name_id = n.id
                WHERE n.name LIKE ?
            """,
                (f"%{name}%",),
            )

        return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]

    def getLocations(self, object_id: int) -> List[Tuple[int, int, int]]:
        """
        Get all spawn locations for an object ID.

        Args:
            object_id: The object ID

        Returns:
            List of (x, y, plane) tuples

        Example:
            >>> objects.getLocations(1276)  # Tree
            [(3200, 3200, 0), (3201, 3200, 0), ...]
        """
        self._ensureConnection()

        cursor = self._db_connection.cursor()
        cursor.execute("SELECT coord FROM objects WHERE object_id = ?", (object_id,))

        locations = []
        for row in cursor.fetchall():
            packed_pos = row[0]
            x, y, plane = unpack_position(packed_pos)
            locations.append((x, y, plane))

        return locations

    def getNearby(self, x: int, y: int, plane: int = 0, radius: int = 10) -> List[Dict[str, Any]]:
        """
        Get all objects near a coordinate (optimized with precise range queries).

        Args:
            x: World X coordinate
            y: World Y coordinate
            plane: Plane/height level (0-3)
            radius: Search radius in tiles

        Returns:
            List of dicts with object info and location

        Example:
            >>> objects.getNearby(3222, 3218, 0, radius=5)
            [{'object_id': 1276, 'name': 'Tree', 'x': 3220, 'y': 3220, 'plane': 0}, ...]
        """
        self._ensureConnection()

        # Calculate coordinate bounds
        min_x = max(0, x - radius)
        max_x = min(32767, x + radius)
        min_y = max(0, y - radius)
        max_y = min(32767, y + radius)

        # Build precise packed position ranges for each X coordinate
        # Since packed format is [plane(2)][x(15)][y(15)], for each X value
        # we can create exact BETWEEN ranges for all Y values in range
        # IMPORTANT: Use signed packing for SQLite compatibility (planes 2-3 become negative)
        ranges = []
        for curr_x in range(min_x, max_x + 1):
            min_packed = pack_position_signed(curr_x, min_y, plane)
            max_packed = pack_position_signed(curr_x, max_y, plane)
            ranges.append((min_packed, max_packed))

        # Build SQL query with OR'd BETWEEN clauses for precise filtering
        or_clauses = " OR ".join(["(o.coord BETWEEN ? AND ?)"] * len(ranges))

        query = f"""
            SELECT o.coord, o.object_id, n.name
            FROM objects o
            LEFT JOIN names n ON o.name_id = n.id
            WHERE {or_clauses}
        """

        # Flatten ranges for query parameters
        params = []
        for min_p, max_p in ranges:
            params.extend([min_p, max_p])

        cursor = self._db_connection.cursor()
        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            packed_pos = row[0]
            obj_x, obj_y, obj_plane = unpack_position(packed_pos)

            # Calculate distance (all results should be within radius)
            dx = abs(obj_x - x)
            dy = abs(obj_y - y)

            results.append(
                {
                    "object_id": row[1],
                    "name": row[2],
                    "x": obj_x,
                    "y": obj_y,
                    "plane": obj_plane,
                    "distance": max(dx, dy),  # Chebyshev distance
                }
            )

        # Sort by distance
        results.sort(key=lambda obj: obj["distance"])

        return results

    def searchByAction(self, action: str) -> List[Dict[str, Any]]:
        """
        Find all objects with a specific action.

        Args:
            action: Action string to search for (e.g., "Bank", "Chop down")

        Returns:
            List of dicts with object info

        Example:
            >>> objects.searchByAction("Bank")
            [{'id': 10356, 'name': '(null)', 'actions': [None, 'Bank', 'Collect', ...]}, ...]
        """
        self._ensureConnection()

        cursor = self._db_connection.cursor()

        # Get all unique objects with this action
        cursor.execute(
            """
            SELECT DISTINCT o.object_id, n.name
            FROM object_action_slots oas
            JOIN objects o ON oas.object_id = o.object_id
            LEFT JOIN names n ON o.name_id = n.id
            WHERE oas.action = ?
        """,
            (action,),
        )

        results = []
        for row in cursor.fetchall():
            object_id = row[0]
            name = row[1]

            # Get all actions for this object
            cursor.execute(
                """
                SELECT slot, action
                FROM object_action_slots
                WHERE object_id = ?
                ORDER BY slot
            """,
                (object_id,),
            )

            # Build actions array [slot0, slot1, slot2, slot3, slot4]
            actions = [None] * 5
            for action_row in cursor.fetchall():
                slot = action_row[0]
                action_text = action_row[1]
                if 0 <= slot <= 4:
                    actions[slot] = action_text

            results.append({"id": object_id, "name": name, "actions": actions})

        return results

    def countObjects(self) -> int:
        """
        Get total number of unique objects in database.

        Returns:
            Total object count
        """
        self._ensureConnection()

        cursor = self._db_connection.cursor()
        cursor.execute("SELECT COUNT(DISTINCT object_id) FROM objects")
        return cursor.fetchone()[0]

    def countLocations(self) -> int:
        """
        Get total number of object spawn locations in database.

        Returns:
            Total location count
        """
        self._ensureConnection()

        cursor = self._db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM objects")
        return cursor.fetchone()[0]

    def executeQuery(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a custom SQL query on the objects database.

        Args:
            query: SQL query string
            params: Query parameters (for ? placeholders)

        Returns:
            List of result rows as dicts

        Example:
            >>> objects.executeQuery("SELECT * FROM objects WHERE name LIKE ? LIMIT 10", ("Tree%",))
            [{'id': 1276, 'name': 'Tree', ...}, ...]
        """
        self._ensureConnection()

        cursor = self._db_connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        if self._db_connection:
            self._db_connection.close()
            self._db_connection = None

    def __del__(self):
        """Cleanup on deletion."""
        self.close()
