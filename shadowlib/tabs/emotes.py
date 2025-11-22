"""
Emotes tab module.
"""

from .gametab import GameTab, GameTabs


class Emotes(GameTabs):
    """
    Emotes tab - displays available emotes.
    """

    TAB_TYPE = GameTab.EMOTES
