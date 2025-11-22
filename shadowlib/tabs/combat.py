"""
Combat tab module.
"""

from .gametab import GameTab, GameTabs


class Combat(GameTabs):
    """
    Combat tab - displays combat stats and special attack.
    """

    TAB_TYPE = GameTab.COMBAT
