"""
Grouping tab module (Clan/Group activities).
"""

from .gametab import GameTab, GameTabs


class Grouping(GameTabs):
    """
    Grouping tab - displays clan chat and group activities.
    """

    TAB_TYPE = GameTab.GROUPING
