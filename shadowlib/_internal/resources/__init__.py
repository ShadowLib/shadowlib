"""
OSRS Game Resources System

Manages downloadable game data (varps, objects, NPCs, items, etc.)
with automatic version checking and updates.

Each resource type is lazy-loaded on first access and automatically
checks for updates based on revision metadata.

Example:
    from src.resources import varps, objects

    # Automatic version checking on first access
    quest_points = varps.getVarpByName("quest_points")

    # Query objects database
    lumbridge_castle = objects.getById(12345)
"""

from .objects import ObjectsResource
from .varps import VarpsResource

# Global singleton instances (lazy-loaded)
_varps_instance = None
_objects_instance = None


def getVarps() -> VarpsResource:
    """Get the global varps resource manager."""
    global _varps_instance
    if _varps_instance is None:
        _varps_instance = VarpsResource()
    return _varps_instance


def getObjects() -> ObjectsResource:
    """Get the global objects resource manager."""
    global _objects_instance
    if _objects_instance is None:
        _objects_instance = ObjectsResource()
    return _objects_instance


# Convenience: expose resource instances directly
varps = getVarps()
objects = getObjects()

__all__ = [
    "varps",
    "objects",
    "get_varps",
    "get_objects",
    "VarpsResource",
    "ObjectsResource",
]
