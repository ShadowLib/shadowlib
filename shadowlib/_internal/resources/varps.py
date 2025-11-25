"""
Varps and Varbits accessor functions.

Data is loaded once at initialization by cache_manager.ensureResourcesLoaded().
This module provides pure accessor functions with no download/update logic.
"""

from typing import Any, Dict

# Module-level data (loaded by cache_manager at init)
_varps_data: Dict[int, Dict[str, Any]] | None = None
_varbits_data: Dict[int, Dict[str, Any]] | None = None


def _getVarpValue(varp_id: int) -> int | None:
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
        from shadowlib.globals import getClient

        client = getClient()
        if hasattr(client, "event_cache"):
            return client.event_cache.getVarp(varp_id)
        return None
    except Exception:
        return None


def extractBits(value: int, start_bit: int, end_bit: int) -> int:
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


def getVarbitInfo(varbit_id: int) -> Dict[str, Any] | None:
    """
    Get metadata about a varbit (which varp it belongs to, bit positions).

    Args:
        varbit_id: The varbit ID to look up

    Returns:
        Dict with keys: 'varp' (int), 'lsb' (int), 'msb' (int), 'name' (str)
        Or None if varbit not found

    Example:
        >>> info = getVarbitInfo(5087)
        >>> # {'varp': 1234, 'lsb': 3, 'msb': 7, 'name': 'example_varbit'}
    """
    if not _varbits_data:
        return None

    varbit_info = _varbits_data.get(varbit_id)
    if not varbit_info:
        return None

    return {
        "varp": varbit_info.get("varp"),
        "lsb": varbit_info.get("lsb", 0),
        "msb": varbit_info.get("msb", 31),
        "name": varbit_info.get("name", f"varbit_{varbit_id}"),
    }


def getVarpByName(name: str) -> int | None:
    """
    Get a varp value by name.

    Args:
        name: The varp name (e.g., "quest_points")

    Returns:
        The varp value, or None if not found

    Example:
        >>> getVarpByName("quest_points")
        250
    """
    if not _varps_data:
        print("❌ Varps data not loaded")
        return None

    # Search for varp by name
    for varp_id, varp_info in _varps_data.items():
        if isinstance(varp_info, dict) and varp_info.get("name") == name:
            return _getVarpValue(int(varp_id))

    print(f"❌ Varp '{name}' not found")
    return None


def getVarpByIndex(varp_id: int) -> int | None:
    """
    Get a varp value by its index.

    Args:
        varp_id: The varp ID to read

    Returns:
        The varp value, or None if not available

    Example:
        >>> getVarpByIndex(273)
        150
    """
    return _getVarpValue(varp_id)


def getVarbitByIndex(varbit_id: int) -> int | None:
    """
    Get a varbit value by its index.

    Args:
        varbit_id: The varbit index

    Returns:
        The varbit value, or None if not found

    Example:
        >>> getVarbitByIndex(5087)
        3
    """
    if not _varbits_data:
        print("❌ Varbits data not loaded")
        return None

    # Get varbit info
    varbit_info = _varbits_data.get(varbit_id)
    if not varbit_info:
        print(f"❌ Varbit {varbit_id} not found")
        return None

    # Get the varp value
    varp_id = varbit_info.get("varp")
    if varp_id is None:
        print(f"❌ Varbit {varbit_id} has no varp mapping")
        return None

    varp_value = _getVarpValue(varp_id)
    if varp_value is None:
        return None

    # Extract the bits
    start_bit = varbit_info.get("lsb", 0)
    end_bit = varbit_info.get("msb", 31)

    return extractBits(varp_value, start_bit, end_bit)


def getVarbitByName(name: str) -> int | None:
    """
    Get a varbit value by name.

    Args:
        name: The varbit name (e.g., "slayer_task_creature")

    Returns:
        The varbit value, or None if not found

    Example:
        >>> getVarbitByName("slayer_task_creature")
        42
    """
    if not _varbits_data:
        print("❌ Varbits data not loaded")
        return None

    # Search for varbit by name
    for varbit_id, varbit_info in _varbits_data.items():
        if isinstance(varbit_info, dict) and varbit_info.get("name") == name:
            return getVarbitByIndex(int(varbit_id))

    print(f"❌ Varbit '{name}' not found")
    return None


def listVarps(filter_name: str | None = None) -> Dict[int, Dict[str, Any]]:
    """
    List all available varps, optionally filtered by name.

    Args:
        filter_name: Optional string to filter varp names

    Returns:
        Dictionary of varp_id -> varp_info
    """
    if not _varps_data:
        return {}

    if filter_name:
        return {
            int(k): v
            for k, v in _varps_data.items()
            if isinstance(v, dict) and filter_name.lower() in v.get("name", "").lower()
        }

    return {int(k): v for k, v in _varps_data.items()}


def listVarbits(filter_name: str | None = None) -> Dict[int, Dict[str, Any]]:
    """
    List all available varbits, optionally filtered by name.

    Args:
        filter_name: Optional string to filter varbit names

    Returns:
        Dictionary of varbit_id -> varbit_info
    """
    if not _varbits_data:
        return {}

    if filter_name:
        return {
            int(k): v
            for k, v in _varbits_data.items()
            if isinstance(v, dict) and filter_name.lower() in v.get("name", "").lower()
        }

    return {int(k): v for k, v in _varbits_data.items()}
