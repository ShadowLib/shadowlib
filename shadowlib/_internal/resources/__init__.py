"""
OSRS Game Resources System

Provides access to game data (varps, varbits, objects) loaded at initialization.
Data is downloaded and loaded once per session by cache_manager.ensureResourcesLoaded().

Example:
    from shadowlib._internal.resources import varps, objects

    # Varps/varbits
    quest_points = varps.getVarpByName("quest_points")
    varbit_value = varps.getVarbitByIndex(5087)

    # Objects
    tree = objects.getById(1276)
    nearby = objects.getNearby(3222, 3218, 0, radius=10)
"""

from . import objects, varps

__all__ = [
    "varps",
    "objects",
]
