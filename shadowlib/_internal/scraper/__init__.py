"""
RuneLite API Scraper and Auto-Updater
"""

from ..updater.api import RuneLiteAPIUpdater

__all__ = ["RuneLiteAPIUpdater", "ensureApiData"]


def ensureApiData(force: bool = False, max_age_days: int = 7, quiet: bool = False) -> bool:
    """
    Convenience function to ensure API data is present and up-to-date.

    This can be called automatically when initializing the RuneLiteAPI.

    Args:
        force: Force update even if up to date
        max_age_days: Maximum age in days before auto-updating (default: 7)
        quiet: Suppress output

    Returns:
        True if API data is ready, False if update failed

    Examples:
        # Ensure data exists (auto-update if needed)
        from src.scraper import ensure_api_data
        ensureApiData()

        # Force update
        ensureApiData(force=True)

        # Check weekly and update if needed
        ensureApiData(max_age_days=7)
    """
    import sys
    from io import StringIO

    updater = RuneLiteAPIUpdater()

    # Redirect output if quiet
    if quiet:
        old_stdout = sys.stdout
        sys.stdout = StringIO()

    try:
        success = updater.update(force=force, max_age_days=max_age_days)
        return success
    finally:
        if quiet:
            sys.stdout = old_stdout
