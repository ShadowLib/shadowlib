"""
Music tab module.
"""

from .gametab import GameTab, GameTabs


class Music(GameTabs):
    """
    Music tab - displays music tracks and player.
    """

    TAB_TYPE = GameTab.MUSIC
