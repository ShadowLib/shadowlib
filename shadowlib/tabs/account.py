"""
Account Management tab module.
"""

from .gametab import GameTab, GameTabs


class Account(GameTabs):
    """
    Account Management tab - displays account settings and info.
    """

    TAB_TYPE = GameTab.ACCOUNT
