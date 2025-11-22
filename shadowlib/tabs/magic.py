"""
Magic tab module.
"""

from .gametab import GameTab, GameTabs


class Magic(GameTabs):
    """
    Magic tab - displays spellbook and available spells.
    """

    TAB_TYPE = GameTab.MAGIC
