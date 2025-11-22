"""
Prayer tab module.
"""

from .gametab import GameTab, GameTabs


class Prayer(GameTabs):
    """
    Prayer tab - displays available prayers and prayer points.
    """

    TAB_TYPE = GameTab.PRAYER
