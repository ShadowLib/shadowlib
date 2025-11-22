#!/usr/bin/env python3
"""
Automatic RuneLite API Updater
Handles downloading, version checking, and automatic regeneration of API data
"""

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple


class RuneLiteAPIUpdater:
    """
    Automatically manages RuneLite API data:
    1. Downloads RuneLite source if missing
    2. Checks for updates via GitHub API
    3. Regenerates API data when needed
    4. Tracks versions to avoid unnecessary work
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize updater.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        if project_root is None:
            # Auto-detect: go up from this file
            # shadowlib/_internal/updater/api.py -> need 4 .parent calls
            project_root = Path(__file__).parent.parent.parent.parent

        self.project_root = Path(project_root)
        self.data_dir = self.project_root / "data" / "api"
        self.temp_dir = self.data_dir / "temp"  # Temporary download location
        self.api_data_file = self.data_dir / "runelite_api_data.json"
        self.version_file = self.data_dir / "runelite_version.json"

        # GitHub API URLs
        self.github_api_url = "https://api.github.com/repos/runelite/runelite"
        self.download_url = "https://github.com/runelite/runelite/archive/refs/heads/master.zip"

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def getCurrentVersion(self) -> Optional[Dict]:
        """Get currently installed version info"""
        if not self.version_file.exists():
            return None

        try:
            with open(self.version_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Could not read version file: {e}")
            return None

    def getLatestGithubVersion(self) -> Optional[Dict]:
        """
        Get latest commit info from GitHub.

        Returns:
            Dict with 'sha', 'date', 'message' or None if failed
        """
        try:
            req = urllib.request.Request(
                f"{self.github_api_url}/commits/master",
                headers={"Accept": "application/vnd.github.v3+json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            return {
                "sha": data["sha"],
                "date": data["commit"]["committer"]["date"],
                "message": data["commit"]["message"].split("\n")[0],  # First line only
                "author": data["commit"]["author"]["name"],
            }

        except urllib.error.URLError as e:
            print(f"⚠️  Could not fetch GitHub version: {e}")
            print("   (Continuing with cached data if available)")
            return None
        except Exception as e:
            print(f"⚠️  Error parsing GitHub response: {e}")
            return None

    def shouldUpdate(self, force: bool = False, max_age_days: int = 7) -> Tuple[bool, str]:
        """
        Determine if update is needed.

        Args:
            force: Force update regardless of version
            max_age_days: Maximum age in days before forcing update

        Returns:
            Tuple of (should_update, reason)
        """
        if force:
            return True, "Forced update requested"

        # Check if API data exists
        if not self.api_data_file.exists():
            return True, "API data not found"

        # Get current version
        current = self.getCurrentVersion()
        if not current:
            return True, "No version info found"

        # Check age
        try:
            last_update = datetime.fromisoformat(current.get("updated_at", "1970-01-01"))
            age = datetime.now() - last_update
            if age > timedelta(days=max_age_days):
                return True, f"Data is {age.days} days old (max: {max_age_days})"
        except Exception:
            pass

        # Check against GitHub
        latest = self.getLatestGithubVersion()
        if latest and current.get("sha") != latest["sha"]:
            return True, f"New commit available: {latest['message'][:50]}"

        return False, "Up to date"

    def downloadRuneliteSource(self) -> Optional[Path]:
        """
        Download RuneLite source code to temporary location.
        Files will be cleaned up automatically after scraping.

        Returns:
            Path to extracted API directory or None if failed
        """
        print("📥 Downloading RuneLite source from GitHub...")

        # Create temp directory for download
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        zip_path = self.temp_dir / "runelite-master.zip"
        extract_path = self.temp_dir / "runelite-master"

        try:
            # Clean up any existing temp files first
            shutil.rmtree(extract_path, ignore_errors=True)
            if zip_path.exists():
                zip_path.unlink()

            # Download with progress
            print(f"   Downloading to {zip_path}")
            urllib.request.urlretrieve(self.download_url, zip_path)
            file_size_mb = zip_path.stat().st_size / 1024 / 1024
            print(f"   ✅ Downloaded {file_size_mb:.1f} MB")

            # Extract
            print("   Extracting ZIP...")

            # Use unzip command
            result = subprocess.run(
                [
                    "unzip",
                    "-q",
                    str(zip_path),
                    "runelite-master/runelite-api/*",
                    "-d",
                    str(self.temp_dir),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"   ⚠️  unzip warning: {result.stderr}")

            api_path = (
                extract_path / "runelite-api" / "src" / "main" / "java" / "net" / "runelite" / "api"
            )

            if not api_path.exists():
                print(f"   ❌ API path not found: {api_path}")
                self.cleanupTempFiles()
                return None

            print(f"   ✅ Extracted to {api_path}")
            return api_path

        except Exception as e:
            print(f"   ❌ Download failed: {e}")
            self.cleanupTempFiles()
            return None

    def cleanupTempFiles(self):
        """Remove temporary download files."""
        if self.temp_dir.exists():
            print("🧹 Cleaning up temporary files...")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("   ✅ Temp files removed")

    def runScraper(self, api_path: Path) -> bool:
        """
        Run the scraper on the API source.

        Args:
            api_path: Path to RuneLite API source

        Returns:
            True if successful
        """
        print("\n🔍 Running scraper on API source...")

        try:
            # Import scraper
            from ..scraper.scraper import EfficientRuneLiteScraper

            # Create scraper and run
            scraper = EfficientRuneLiteScraper()
            scraper.scrapeLocalDirectory(api_path)

            # Save to correct location
            output_file = self.api_data_file
            scraper.save(str(output_file))

            # Verify it was created
            if not output_file.exists():
                print("❌ API data file was not created")
                return False

            # Check it has data
            with open(output_file) as f:
                data = json.load(f)

            if len(data.get("methods", {})) == 0:
                print("❌ API data is empty")
                return False

            print(f"✅ API data saved to {output_file}")
            print(f"   Methods: {len(data['methods'])}")
            print(f"   Enums: {len(data['enums'])}")
            print(f"   Classes: {len(data['classes'])}")

            return True

        except Exception as e:
            print(f"❌ Scraper failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def updateVersionInfo(self):
        """Save version information after successful update"""
        version_info = {
            "updated_at": datetime.now().isoformat(),
            "data_file": str(self.api_data_file),
        }

        # Add GitHub info if available
        github_info = self.getLatestGithubVersion()
        if github_info:
            version_info.update(github_info)

        with open(self.version_file, "w") as f:
            json.dump(version_info, f, indent=2)

        print(f"\n✅ Version info saved to {self.version_file}")

    def regenerateProxies(self) -> bool:
        """
        Regenerate proxy classes and constants from API data.

        Returns:
            True if successful
        """
        print("\n🔄 Regenerating proxy classes and constants...")

        generated_dir = self.project_root / "shadowlib" / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)

        proxy_file = generated_dir / "query_proxies.py"
        constants_file = generated_dir / "constants.py"

        try:
            # Import proxy generator
            from ..scraper.proxy_generator import ProxyGenerator

            # Generate proxies (takes file path, not dict)
            generator = ProxyGenerator(str(self.api_data_file))
            generator.saveProxies(str(proxy_file))
            generator.saveConstants(str(constants_file))

            # Verify they were created
            if not proxy_file.exists():
                print("❌ Proxy file was not created")
                return False

            if not constants_file.exists():
                print("❌ Constants file was not created")
                return False

            proxy_size_kb = proxy_file.stat().st_size / 1024
            constants_size_kb = constants_file.stat().st_size / 1024
            print(f"✅ Proxy file generated: {proxy_size_kb:.1f} KB")
            print(f"✅ Constants file generated: {constants_size_kb:.1f} KB")

            return True

        except Exception as e:
            print(f"❌ Generation failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def update(self, force: bool = False, max_age_days: int = 7) -> bool:
        """
        Main update function - checks and updates if needed.

        Args:
            force: Force update even if up to date
            max_age_days: Maximum age before forcing update

        Returns:
            True if update was successful or not needed
        """
        print("=" * 80)
        print("🚀 RuneLite API Auto-Updater")
        print("=" * 80)

        # Check if update needed
        needs_update, reason = self.shouldUpdate(force, max_age_days)

        if not needs_update:
            print(f"\n✅ {reason}")
            return True

        print(f"\n📋 Update needed: {reason}")

        # Always download fresh source (no caching)
        # Download to temp directory
        api_path = self.downloadRuneliteSource()
        if not api_path:
            print("\n❌ Failed to download RuneLite source")
            return False

        # Run scraper
        scrape_success = self.runScraper(api_path)

        # Always cleanup temp files after scraping (success or failure)
        self.cleanupTempFiles()

        if not scrape_success:
            print("\n❌ Scraper failed")
            return False

        # Regenerate proxies before updating version file
        # This ensures we don't mark as "updated" if proxy generation fails
        proxy_success = self.regenerateProxies()
        if not proxy_success:
            print("\n❌ Proxy generation failed")
            return False

        # Update version info LAST - only after everything succeeds
        # This prevents stale cache if we crash mid-run
        self.updateVersionInfo()

        print("\n" + "=" * 80)
        print("✅ Update complete!")
        print("=" * 80)

        return True

    def cleanTempFiles(self):
        """Remove temporary download files (alias for cleanupTempFiles)"""
        self.cleanupTempFiles()

    def status(self):
        """Print current status"""
        print("=" * 80)
        print("📊 RuneLite API Status")
        print("=" * 80)

        # Check API data
        if self.api_data_file.exists():
            size_mb = self.api_data_file.stat().st_size / 1024 / 1024
            print(f"\n✅ API data exists: {self.api_data_file}")
            print(f"   Size: {size_mb:.2f} MB")

            try:
                with open(self.api_data_file) as f:
                    data = json.load(f)
                print(f"   Methods: {len(data.get('methods', {}))}")
                print(f"   Enums: {len(data.get('enums', {}))}")
                print(f"   Classes: {len(data.get('classes', []))}")
            except Exception as e:
                print(f"   ⚠️  Could not read data: {e}")
        else:
            print(f"\n❌ API data not found: {self.api_data_file}")

        # Check version
        version = self.getCurrentVersion()
        if version:
            print("\n📌 Current version:")
            print(f"   Updated: {version.get('updated_at', 'unknown')}")
            print(f"   Commit: {version.get('sha', 'unknown')[:8]}")
            print(f"   Message: {version.get('message', 'unknown')}")
        else:
            print("\n⚠️  No version information")

        # Check for updates
        print("\n🔍 Checking for updates...")
        latest = self.getLatestGithubVersion()
        if latest:
            print(f"   Latest commit: {latest['sha'][:8]}")
            print(f"   Date: {latest['date']}")
            print(f"   Message: {latest['message']}")

            if version and version.get("sha") == latest["sha"]:
                print("\n✅ Up to date!")
            else:
                print("\n⚠️  Update available")
        else:
            print("   ⚠️  Could not check GitHub")

        # Check temp directory
        if self.temp_dir.exists():
            temp_files = list(self.temp_dir.iterdir())
            if temp_files:
                print(f"\n⚠️  Temp files exist (should be cleaned): {len(temp_files)} files")
            else:
                print("\n✅ No temp files")
        else:
            print("\n✅ No temp directory")
