"""
GameTabs package - contains all game tab modules for OSRS.

Each tab inherits from the base GameTabs class and provides
tab-specific functionality for the Old School RuneScape interface.
"""

from .account import Account
from .combat import Combat
from .emotes import Emotes
from .equipment import Equipment
from .friends import Friends
from .gametab import GameTab, GameTabs
from .grouping import Grouping
from .inventory import Inventory
from .logout import Logout
from .magic import Magic
from .music import Music
from .prayer import Prayer
from .progress import Progress
from .settings import Settings
from .skills import Skills

__all__ = [
    "GameTab",
    "GameTabs",
    "Combat",
    "Skills",
    "Progress",
    "Inventory",
    "Equipment",
    "Prayer",
    "Magic",
    "Grouping",
    "Friends",
    "Account",
    "Settings",
    "Logout",
    "Emotes",
    "Music",
]
