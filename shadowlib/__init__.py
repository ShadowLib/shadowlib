"""
ShadowLib - OSRS Bot Development SDK

A Python SDK for Old School RuneScape bot development with an intuitive
structure that mirrors the game's interface.
"""

__version__ = "3.2.0"
__author__ = "ShadowBot Team"

# Ensure generated files path is available for imports
from shadowlib._internal.cache_manager import ensureGeneratedInPath

ensureGeneratedInPath()

from shadowlib.client import Client  # noqa: E402

__all__ = ["Client"]
