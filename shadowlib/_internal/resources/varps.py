"""
Varps and Varbits resource manager.

Handles downloading and querying varp/varbit definitions with automatic updates.
"""

import json
from typing import Any, Dict, Optional

from .base import BaseResource


class VarpsResource(BaseResource):
    """
    Manages varp and varbit data with automatic version checking and updates.

    Varps are 32-bit integers in OSRS that store game state.
    Varbits map to specific bit ranges within varps.
    """

    def __init__(self):
        super().__init__("varps")
        self._varps_data = None
        self._varbits_data = None

    def getRemoteFiles(self) -> Dict[str, str]:
        """Specify which files to download."""
        return {
            "varps.json": "varps.json",
            "varbits.json": "varbits.json",
            "metadata.json": "metadata.json",
        }

    def _loadDataFiles(self):
        """Load varps and varbits from cached JSON files."""
        try:
            # Load varps
            varps_file = self.cache_dir / "varps.json"
            if varps_file.exists():
                with open(varps_file) as f:
                    raw_varps = json.load(f)
                # Convert list to dict indexed by ID
                if isinstance(raw_varps, list):
                    self._varps_data = {item["id"]: item for item in raw_varps if "id" in item}
                else:
                    self._varps_data = raw_varps
                print(f"✅ Loaded {len(self._varps_data)} varps")

            # Load varbits
            varbits_file = self.cache_dir / "varbits.json"
            if varbits_file.exists():
                with open(varbits_file) as f:
                    raw_varbits = json.load(f)
                # Convert list to dict indexed by ID
                if isinstance(raw_varbits, list):
                    self._varbits_data = {item["id"]: item for item in raw_varbits if "id" in item}
                else:
                    self._varbits_data = raw_varbits
                print(f"✅ Loaded {len(self._varbits_data)} varbits")

        except Exception as e:
            print(f"❌ Failed to load varp/varbit data: {e}")
            raise

    def getVarpValue(self, varp_id: int) -> Optional[int]:
        """
        Get the current value of a varp from the event cache.

        Uses cached varp values (updated from varbit_changed events)
        instead of direct API queries for better performance.

        Args:
            varp_id: The varp ID to read

        Returns:
            The 32-bit integer value, or None if not available
        """
        try:
            # Get from event cache instead of direct query
            from shadowlib.globals import getClient

            client = getClient()
            return client.cache.getVarp(varp_id)

        except Exception as e:
            print(f"⚠️  Failed to read varp {varp_id}: {e}")
            return None

    def extractBits(self, value: int, start_bit: int, end_bit: int) -> int:
        """
        Extract bits from a varp value.

        Args:
            value: The 32-bit varp value
            start_bit: Starting bit position (0-31)
            end_bit: Ending bit position (0-31)

        Returns:
            The extracted value
        """
        num_bits = end_bit - start_bit + 1
        mask = (1 << num_bits) - 1
        return (value >> start_bit) & mask

    def getVarbitInfo(self, varbit_id: int) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a varbit (which varp it belongs to, bit positions).

        Args:
            varbit_id: The varbit ID to look up

        Returns:
            Dict with keys: 'varp' (int), 'lsb' (int), 'msb' (int), 'name' (str)
            Or None if varbit not found

        Example:
            >>> info = varps.getVarbitInfo(5087)
            >>> # {'varp': 1234, 'lsb': 3, 'msb': 7, 'name': 'example_varbit'}
        """
        self.ensureLoaded()

        if not self._varbits_data:
            return None

        varbit_info = self._varbits_data.get(varbit_id)
        if not varbit_info:
            return None

        return {
            "varp": varbit_info.get("varp"),
            "lsb": varbit_info.get("lsb", 0),
            "msb": varbit_info.get("msb", 31),
            "name": varbit_info.get("name", f"varbit_{varbit_id}"),
        }

    def getVarpByName(self, name: str) -> Optional[int]:
        """
        Get a varp value by name.

        Args:
            name: The varp name (e.g., "quest_points")

        Returns:
            The varp value, or None if not found

        Example:
            >>> varps.getVarpByName("quest_points")
            250
        """
        self.ensureLoaded()

        if not self._varps_data:
            print("❌ Varps data not loaded")
            return None

        # Search for varp by name
        for varp_id, varp_info in self._varps_data.items():
            if isinstance(varp_info, dict) and varp_info.get("name") == name:
                return self.getVarpValue(int(varp_id))

        print(f"❌ Varp '{name}' not found")
        return None

    def getVarpByIndex(self, varp_id: int) -> Optional[int]:
        """
        Get a varp value by its index.

        Args:
            varp_id: The varp ID to read

        Returns:
            The varp value, or None if not available

        Example:
            >>> varps.getVarpByIndex(273)
            150
        """
        self.ensureLoaded()
        return self.getVarpValue(varp_id)

    def getVarbitByIndex(self, varbit_id: int) -> Optional[int]:
        """
        Get a varbit value by its index.

        Args:
            varbit_id: The varbit index

        Returns:
            The varbit value, or None if not found

        Example:
            >>> varps.getVarbitByIndex(5087)
            3
        """
        self.ensureLoaded()

        if not self._varbits_data:
            print("❌ Varbits data not loaded")
            return None

        # Get varbit info
        varbit_info = self._varbits_data.get(varbit_id)
        if not varbit_info:
            print(f"❌ Varbit {varbit_id} not found")
            return None

        # Get the varp value
        varp_id = varbit_info.get("varp")
        if varp_id is None:
            print(f"❌ Varbit {varbit_id} has no varp mapping")
            return None

        varp_value = self.getVarpValue(varp_id)
        if varp_value is None:
            return None

        # Extract the bits
        start_bit = varbit_info.get("lsb", 0)
        end_bit = varbit_info.get("msb", 31)

        return self.extractBits(varp_value, start_bit, end_bit)

    def getVarbitByName(self, name: str) -> Optional[int]:
        """
        Get a varbit value by name.

        Args:
            name: The varbit name (e.g., "slayer_task_creature")

        Returns:
            The varbit value, or None if not found

        Example:
            >>> varps.getVarbitByName("slayer_task_creature")
            42
        """
        self.ensureLoaded()

        if not self._varbits_data:
            print("❌ Varbits data not loaded")
            return None

        # Search for varbit by name
        for varbit_id, varbit_info in self._varbits_data.items():
            if isinstance(varbit_info, dict) and varbit_info.get("name") == name:
                return self.getVarbitByIndex(int(varbit_id))

        print(f"❌ Varbit '{name}' not found")
        return None

    def listVarps(self, filter_name: Optional[str] = None) -> Dict[int, Dict[str, Any]]:
        """
        List all available varps, optionally filtered by name.

        Args:
            filter_name: Optional string to filter varp names

        Returns:
            Dictionary of varp_id -> varp_info
        """
        self.ensureLoaded()

        if not self._varps_data:
            return {}

        if filter_name:
            return {
                int(k): v
                for k, v in self._varps_data.items()
                if isinstance(v, dict) and filter_name.lower() in v.get("name", "").lower()
            }

        return {int(k): v for k, v in self._varps_data.items()}

    def listVarbits(self, filter_name: Optional[str] = None) -> Dict[int, Dict[str, Any]]:
        """
        List all available varbits, optionally filtered by name.

        Args:
            filter_name: Optional string to filter varbit names

        Returns:
            Dictionary of varbit_id -> varbit_info
        """
        self.ensureLoaded()

        if not self._varbits_data:
            return {}

        if filter_name:
            return {
                int(k): v
                for k, v in self._varbits_data.items()
                if isinstance(v, dict) and filter_name.lower() in v.get("name", "").lower()
            }

        return {int(k): v for k, v in self._varbits_data.items()}
