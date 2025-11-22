"""
Equipment tab module.
"""

from .gametab import GameTab, GameTabs


class Equipment(GameTabs):
    """
    Equipment tab - displays worn equipment and stats.
    """

    TAB_TYPE = GameTab.EQUIPMENT
