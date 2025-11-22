"""
Progress tab module (Quest/Achievement Diaries).
"""

from .gametab import GameTab, GameTabs


class Progress(GameTabs):
    """
    Progress tab - displays quests and achievement diaries.
    """

    TAB_TYPE = GameTab.PROGRESS
