#!/usr/bin/env python3
"""
Resource Auto-Updater for Varps and Objects Database

Handles automatic version checking and updating of game resources
separately from RuneLite API updates.
"""

from pathlib import Path
from typing import Optional, Tuple


class ResourceUpdater:
    """
    Manages automatic updates for game resources (varps, objects, etc.)
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize resource updater.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        if project_root is None:
            # Auto-detect: go up from this file
            # shadowlib/_internal/updater/resources.py -> need 4 .parent calls
            project_root = Path(__file__).parent.parent.parent.parent

        self.project_root = Path(project_root)
        self.resources_dir = self.project_root / "data" / "resources"

    def shouldUpdateVarps(self) -> Tuple[bool, str]:
        """
        Check if varps resource needs update.

        Returns:
            Tuple of (should_update, reason)
        """
        from ..resources.varps import VarpsResource

        try:
            varps = VarpsResource()
            # Check if needs update (checks remote metadata)
            if varps._needsUpdate():
                return True, "Varps update available"
            return False, "Varps up to date"
        except Exception as e:
            return True, f"Varps check failed: {e}"

    def shouldUpdateObjects(self) -> Tuple[bool, str]:
        """
        Check if objects database needs update.

        Returns:
            Tuple of (should_update, reason)
        """
        from ..resources.objects import ObjectsResource

        try:
            objects = ObjectsResource()
            # Check if needs update (checks remote metadata)
            if objects._needsUpdate():
                return True, "Objects database update available"
            return False, "Objects database up to date"
        except Exception as e:
            return True, f"Objects check failed: {e}"

    def updateVarps(self, force: bool = False) -> bool:
        """
        Update varps resource.

        Args:
            force: Force update even if up to date

        Returns:
            True if successful
        """
        print("\n📦 Updating Varps resource...")

        try:
            from ..resources.varps import VarpsResource

            varps = VarpsResource()
            varps.ensureLoaded(force_update=force)
            print("✅ Varps updated successfully")
            return True

        except Exception as e:
            print(f"❌ Varps update failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def updateObjects(self, force: bool = False) -> bool:
        """
        Update objects database.

        Args:
            force: Force update even if up to date

        Returns:
            True if successful
        """
        print("\n📦 Updating Objects database...")

        try:
            from ..resources.objects import ObjectsResource

            objects = ObjectsResource()
            objects.ensureLoaded(force_update=force)
            print("✅ Objects database updated successfully")
            return True

        except Exception as e:
            print(f"❌ Objects update failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def shouldUpdateAny(self) -> Tuple[bool, str]:
        """
        Check if any resource needs update.

        Returns:
            Tuple of (should_update, reason)
        """
        needs_update = False
        reasons = []

        # Check varps
        varps_update, varps_reason = self.shouldUpdateVarps()
        if varps_update:
            needs_update = True
            reasons.append(f"Varps: {varps_reason}")

        # Check objects
        objects_update, objects_reason = self.shouldUpdateObjects()
        if objects_update:
            needs_update = True
            reasons.append(f"Objects: {objects_reason}")

        if needs_update:
            return True, ", ".join(reasons)
        return False, "All resources up to date"

    def updateAll(self, force: bool = False) -> bool:
        """
        Update all resources atomically.

        This is an all-or-nothing operation - if any resource needs update,
        ALL resources are updated together. This prevents desync issues
        since varps and objects share metadata.json.

        Args:
            force: Force update even if up to date

        Returns:
            True if all updates successful
        """
        print("=" * 80)
        print("🔄 Resource Auto-Updater")
        print("=" * 80)

        # Check if any resource needs update BEFORE updating any
        if not force:
            needs_update, reason = self.shouldUpdateAny()
            if not needs_update:
                print(f"✅ {reason}")
                print("=" * 80)
                return True
            print(f"📦 {reason}")

        success = True

        # Update all resources together (atomic operation)
        print("\n🔄 Updating all resources...")

        # Update varps
        if not self.updateVarps(force=force):
            success = False

        # Update objects
        if not self.updateObjects(force=force):
            success = False

        if success:
            print("\n" + "=" * 80)
            print("✅ All resources updated successfully!")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ Resource update failed - some resources may be out of sync")
            print("=" * 80)

        return success

    def status(self):
        """Print current resource status."""
        print("=" * 80)
        print("📊 Resource Status")
        print("=" * 80)

        # Check varps
        print("\n🔹 Varps Resource:")
        needs_update, reason = self.shouldUpdateVarps()
        if needs_update:
            print(f"   ⚠️  {reason}")
        else:
            print(f"   ✅ {reason}")

        # Check objects
        print("\n🔹 Objects Database:")
        needs_update, reason = self.shouldUpdateObjects()
        if needs_update:
            print(f"   ⚠️  {reason}")
        else:
            print(f"   ✅ {reason}")

        print("\n" + "=" * 80)


def main():
    """Command-line interface for resource updater."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Resource Auto-Updater",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all resources
  python -m shadowlib._internal.scraper.resource_updater

  # Force update
  python -m shadowlib._internal.scraper.resource_updater --force

  # Check status only
  python -m shadowlib._internal.scraper.resource_updater --status
""",
    )

    parser.add_argument(
        "--force", "-f", action="store_true", help="Force update even if up to date"
    )

    parser.add_argument(
        "--status", "-s", action="store_true", help="Show status only, do not update"
    )

    args = parser.parse_args()

    updater = ResourceUpdater()

    if args.status:
        updater.status()
    else:
        success = updater.updateAll(force=args.force)
        exit(0 if success else 1)


if __name__ == "__main__":
    main()
