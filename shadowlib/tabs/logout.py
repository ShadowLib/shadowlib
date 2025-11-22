"""
Logout tab module.
"""

from .gametab import GameTab, GameTabs


class Logout(GameTabs):
    """
    Logout tab - displays logout options and world switcher.
    """

    TAB_TYPE = GameTab.LOGOUT
