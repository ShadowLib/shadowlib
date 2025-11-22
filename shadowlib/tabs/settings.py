"""
Settings tab module.
"""

from .gametab import GameTab, GameTabs


class Settings(GameTabs):
    """
    Settings tab - displays game settings and controls.
    """

    TAB_TYPE = GameTab.SETTINGS
