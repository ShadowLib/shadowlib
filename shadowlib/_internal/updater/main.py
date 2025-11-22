#!/usr/bin/env python3
"""
Main auto-updater entry point.

Handles updating all shadowlib data:
- RuneLite API data
- Game resources (varps, objects database)
"""


def main():
    """Command-line interface for shadowlib updater"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Shadow Bot SDK Auto-Updater",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update everything (API + resources) - default behavior
  python -m shadowlib._internal.updater

  # Force update everything
  python -m shadowlib._internal.updater --force

  # Check status of all data
  python -m shadowlib._internal.updater --status

  # Update only RuneLite API (skip resources)
  python -m shadowlib._internal.updater --api-only

  # Update only resources (skip API)
  python -m shadowlib._internal.updater --resources-only

  # Clean temporary files
  python -m shadowlib._internal.updater --clean
""",
    )

    parser.add_argument(
        "--force", "-f", action="store_true", help="Force update even if up to date"
    )

    parser.add_argument(
        "--max-age-days",
        type=int,
        default=7,
        help="Maximum age in days before forcing API update (default: 7)",
    )

    parser.add_argument(
        "--status", "-s", action="store_true", help="Show status only, do not update"
    )

    parser.add_argument("--clean", "-c", action="store_true", help="Clean temporary download files")

    parser.add_argument(
        "--api-only", action="store_true", help="Only update RuneLite API, skip game resources"
    )

    parser.add_argument(
        "--resources-only",
        action="store_true",
        help="Only update game resources, skip RuneLite API",
    )

    args = parser.parse_args()

    # Default behavior: update both API and resources
    update_resources = not args.api_only
    update_api = not args.resources_only

    resource_success = True
    api_success = True

    # Handle resource updates (default: ON)
    if update_resources:
        from .resources import ResourceUpdater

        resource_updater = ResourceUpdater()

        if args.status:
            resource_updater.status()
            if update_api:
                print()  # Spacing between resource and API status
        elif not args.clean:
            resource_success = resource_updater.updateAll(force=args.force)

    # Handle RuneLite API updates (default: ON)
    if update_api:
        from .api import RuneLiteAPIUpdater

        api_updater = RuneLiteAPIUpdater()

        if args.status:
            api_updater.status()
        elif args.clean:
            api_updater.cleanTempFiles()
        else:
            api_success = api_updater.update(force=args.force, max_age_days=args.max_age_days)

    # Exit with success only if all enabled updates succeeded
    if not args.status and not args.clean:
        exit(0 if (resource_success and api_success) else 1)


if __name__ == "__main__":
    main()
