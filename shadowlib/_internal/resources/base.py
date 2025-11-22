"""
Base resource manager with automatic version checking and updates.

All game resources (varps, objects, NPCs, items, etc.) inherit from this base class.
"""

import gzip
import json
import shutil
import time
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

# Base cache directory for all resources in project root
# shadowlib/_internal/resources/base.py -> _internal -> shadowlib -> project root
RESOURCES_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "resources"

# Base URL for all resources
BASE_URL = "https://storage.googleapis.com/osrs-chroma-storage-eu"


class BaseResource(ABC):
    """
    Base class for all downloadable game resources.

    Handles:
    - Automatic version checking against remote metadata
    - Downloads only when revision changes
    - Decompression of .gz files
    - Caching to local filesystem
    - Thread-safe lazy loading
    """

    def __init__(self, resource_type: str, shared_metadata_with: str = None):
        """
        Initialize base resource manager.

        Args:
            resource_type: Resource type name (e.g., "varps", "objects", "npcs")
            shared_metadata_with: If set, use metadata from another resource's cache dir
        """
        self.resource_type = resource_type
        self.cache_dir = RESOURCES_CACHE_DIR / resource_type
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Metadata location (can be shared)
        if shared_metadata_with:
            self.metadata_cache_dir = RESOURCES_CACHE_DIR / shared_metadata_with
        else:
            self.metadata_cache_dir = self.cache_dir

        # Resource-specific URLs (subclass overrides)
        self.base_url = f"{BASE_URL}/{resource_type}/latest"

        # Lazy-loaded data
        self._data = None
        self._metadata = None
        self._loaded = False
        self._last_check_time = 0
        self._check_interval = 60  # Check at most once per minute  # Check at most once per minute

    @abstractmethod
    def getRemoteFiles(self) -> Dict[str, str]:
        """
        Return dict of remote files to download.

        Returns:
            Dict mapping local filename -> remote filename
            Example: {"data.json": "varps.json", "metadata.json": "metadata.json"}
        """
        pass

    @abstractmethod
    def _loadDataFiles(self):
        """Load data from cached files into self._data."""
        pass

    def _downloadFile(self, url: str, dest: Path, decompress_gz: bool = True) -> bool:
        """
        Download a file from URL to destination.

        Args:
            url: URL to download from
            dest: Local destination path
            decompress_gz: If True and URL ends with .gz, decompress after download

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"📥 Downloading {url}...")

            # Create request with cache-busting headers
            req = urllib.request.Request(url)
            req.add_header("Cache-Control", "no-cache, no-store, must-revalidate")
            req.add_header("Pragma", "no-cache")
            req.add_header("Expires", "0")

            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()

                # Handle gzip decompression
                if decompress_gz and url.endswith(".gz"):
                    # Write compressed file temporarily
                    gz_file = dest.with_suffix(dest.suffix + ".gz")
                    with open(gz_file, "wb") as f:
                        f.write(data)

                    print(f"💾 Downloaded: {gz_file.stat().st_size:,} bytes")

                    # Decompress to working file
                    print(f"📦 Decompressing {gz_file.name}...")
                    with gzip.open(gz_file, "rb") as f_in:
                        with open(dest, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    print(f"✅ Decompressed: {dest.stat().st_size:,} bytes")

                    # Delete the .gz file after decompression
                    gz_file.unlink()
                    print("🗑️  Removed compressed file")
                else:
                    # Write directly
                    with open(dest, "wb") as f:
                        f.write(data)
                    print(f"✅ Downloaded: {dest.stat().st_size:,} bytes")

            return True

        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")
            return False

    def _getLocalMetadata(self) -> Optional[Dict[str, Any]]:
        """Get locally cached metadata."""
        metadata_file = self.metadata_cache_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load local metadata: {e}")
        return None

    def _getRemoteMetadata(self) -> Optional[Dict[str, Any]]:
        """Fetch remote metadata to check current revision."""
        url = f"{self.base_url}/metadata.json"
        try:
            req = urllib.request.Request(url)
            req.add_header("Cache-Control", "no-cache")
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                return json.loads(data)
        except Exception as e:
            print(f"⚠️  Failed to fetch remote metadata: {e}")
            return None

    def _needsUpdate(self) -> bool:
        """
        Check if local cache needs updating.

        Returns:
            True if update needed, False otherwise
        """
        # Rate limit checks (don't spam the server)
        current_time = time.time()
        if current_time - self._last_check_time < self._check_interval:
            return False
        self._last_check_time = current_time

        # Get remote metadata
        remote_meta = self._getRemoteMetadata()
        if remote_meta is None:
            # Can't reach server, use cached data if available
            return not self._hasCachedFiles()

        # Get local metadata
        local_meta = self._getLocalMetadata()

        # Compare revisions (try 'cache_id' first, then 'revision')
        remote_revision = remote_meta.get("cache_id") or remote_meta.get("revision")
        local_revision = None
        if local_meta:
            local_revision = local_meta.get("cache_id") or local_meta.get("revision")

        if remote_revision is None:
            # No revision info, check if files exist
            if not self._hasCachedFiles():
                print(f"🔄 No local cache for {self.resource_type}, downloading...")
                return True
            return False

        if local_revision is None:
            print(f"🔄 No local cache for {self.resource_type}, downloading...")
            return True

        if remote_revision != local_revision:
            print(
                f"🔄 New revision available for {self.resource_type}: {local_revision} → {remote_revision}"
            )
            return True

        # Revisions match, but check if files actually exist
        # (handles case where metadata was downloaded but data files weren't)
        if not self._hasCachedFiles():
            print(f"🔄 Cache files missing for {self.resource_type}, downloading...")
            return True

        return False

    def _hasCachedFiles(self) -> bool:
        """Check if all required files are cached locally."""
        files = self.getRemoteFiles()
        for local_name in files.keys():
            if not (self.cache_dir / local_name).exists():
                return False
        return True

    def _downloadAll(self) -> bool:
        """
        Download all resource files.

        Returns:
            True if all downloads successful, False otherwise
        """
        files = self.getRemoteFiles()
        success = True

        for local_name, remote_name in files.items():
            url = f"{self.base_url}/{remote_name}"
            dest = self.cache_dir / local_name
            decompress = remote_name.endswith(".gz")

            if not self._downloadFile(url, dest, decompress_gz=decompress):
                success = False

        return success

    def ensureLoaded(self, force_update: bool = False):
        """
        Ensure resource data is loaded, downloading if necessary.

        Args:
            force_update: If True, force re-download even if cache is current
        """
        if self._loaded and not force_update:
            return

        # Check if update needed
        if force_update or self._needsUpdate():
            print(f"⬇️  Updating {self.resource_type}...")
            if self._downloadAll():
                print(f"✅ {self.resource_type} updated successfully")
            else:
                print(f"⚠️  Some files failed to download for {self.resource_type}")

        # Load data from cache
        if not self._hasCachedFiles():
            raise FileNotFoundError(
                f"Required cache files missing for {self.resource_type}. "
                f"Check your internet connection."
            )

        self._loadDataFiles()
        self._loaded = True

    def forceUpdate(self):
        """
        Force fresh download of all resource files, bypassing cache.

        Use this if you suspect cached data is corrupted or outdated.
        """
        print(f"🔄 Forcing fresh download for {self.resource_type}...")
        self.ensureLoaded(forceUpdate=True)

    def getRevision(self) -> Optional[str]:
        """
        Get current local revision/cache_id.

        Returns:
            Revision string, or None if not available
        """
        meta = self._getLocalMetadata()
        if meta:
            return meta.get("cache_id") or meta.get("revision")
        return None

    def getMetadata(self) -> Optional[Dict[str, Any]]:
        """
        Get full metadata for this resource.

        Returns:
            Metadata dict, or None if not available
        """
        return self._getLocalMetadata()
