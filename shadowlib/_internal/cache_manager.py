"""
Centralized cache management for ShadowLib.

Uses ~/.cache/shadowlib/ for all generated files and resources following XDG Base Directory specification.

This module also handles:
- Downloading and loading game resources (varps, objects) at initialization
- Managing generated files (query proxies, constants) in cache
- Ensuring generated modules are importable via sys.path
"""

import gzip
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


class CacheManager:
    """Manages cache directories for ShadowLib resources and generated files."""

    def __init__(self, base_path: Path | None = None):
        """
        Initialize cache manager.

        Args:
            base_path: Optional custom base path. If None, uses ~/.cache/shadowlib
        """
        if base_path is None:
            # Use XDG_CACHE_HOME if set, otherwise default to ~/.cache
            xdg_cache = os.getenv("XDG_CACHE_HOME")
            if xdg_cache:
                self.base_path = Path(xdg_cache) / "shadowlib"
            else:
                self.base_path = Path.home() / ".cache" / "shadowlib"
        else:
            self.base_path = Path(base_path)

        # Define standard cache directories
        self.generated_dir = self.base_path / "generated"
        self.data_dir = self.base_path / "data"
        self.objects_dir = self.data_dir / "objects"
        self.varps_dir = self.data_dir / "varps"

    def ensureDirs(self) -> None:
        """Create all cache directories if they don't exist."""
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.varps_dir.mkdir(parents=True, exist_ok=True)

    def getGeneratedPath(self, filename: str) -> Path:
        """
        Get path for a generated file.

        Args:
            filename: Name of the generated file

        Returns:
            Full path to the file in ~/.cache/shadowlib/generated/
        """
        return self.generated_dir / filename

    def getObjectsPath(self) -> Path:
        """
        Get path for objects data directory.

        Returns:
            Path to ~/.cache/shadowlib/data/objects/
        """
        return self.objects_dir

    def getVarpsPath(self) -> Path:
        """
        Get path for varps data directory.

        Returns:
            Path to ~/.cache/shadowlib/data/varps/
        """
        return self.varps_dir

    def getDataPath(self, resource_type: str) -> Path:
        """
        Get path for a specific resource type.

        Args:
            resource_type: Type of resource (e.g., 'objects', 'varps')

        Returns:
            Path to the resource directory
        """
        return self.data_dir / resource_type

    def clearCache(self) -> None:
        """Clear all cached files (use with caution)."""
        import shutil

        if self.base_path.exists():
            shutil.rmtree(self.base_path)

    def getCacheSize(self) -> int:
        """
        Get total size of cache in bytes.

        Returns:
            Total cache size in bytes
        """
        total = 0
        if self.base_path.exists():
            for path in self.base_path.rglob("*"):
                if path.is_file():
                    total += path.stat().st_size
        return total


# Global cache manager instance
_cache_manager: CacheManager | None = None


def getCacheManager() -> CacheManager:
    """
    Get global cache manager instance.

    Returns:
        Global CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        _cache_manager.ensureDirs()
    return _cache_manager


# =============================================================================
# Game Resources Download & Initialization
# =============================================================================

# Base URL for game resources
BASE_URL = "https://storage.googleapis.com/osrs-chroma-storage-eu"

# Track if resources have been loaded this session
_resources_loaded = False


def _downloadFile(url: str, dest: Path, decompress_gz: bool = True) -> bool:
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


def _getRemoteMetadata() -> dict | None:
    """
    Fetch remote metadata to check current revision.

    Returns:
        Metadata dict or None if fetch fails
    """
    url = f"{BASE_URL}/varps/latest/metadata.json"
    try:
        req = urllib.request.Request(url)
        req.add_header("Cache-Control", "no-cache")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
            return json.loads(data)
    except Exception as e:
        print(f"⚠️  Failed to fetch remote metadata: {e}")
        return None


def _needsUpdate(cache_dir: Path) -> bool:
    """
    Check if resources need updating.

    Args:
        cache_dir: Path to game_data cache directory

    Returns:
        True if update needed, False otherwise
    """
    # Check if files exist
    required_files = ["metadata.json", "varps.json", "varbits.json", "objects.db"]
    if not all((cache_dir / f).exists() for f in required_files):
        print("🔄 Resources not found locally, downloading...")
        return True

    # Get remote metadata
    remote_meta = _getRemoteMetadata()
    if remote_meta is None:
        # Can't reach server, use cached data if available
        return False

    # Get local metadata
    metadata_file = cache_dir / "metadata.json"
    try:
        with open(metadata_file) as f:
            local_meta = json.load(f)
    except Exception:
        return True

    # Compare revisions
    remote_revision = remote_meta.get("cache_id") or remote_meta.get("revision")
    local_revision = local_meta.get("cache_id") or local_meta.get("revision")

    if remote_revision and local_revision and remote_revision != local_revision:
        print(f"🔄 New revision available: {local_revision} → {remote_revision}")
        return True

    return False


def ensureResourcesLoaded() -> bool:
    """
    Ensure game resources are downloaded and loaded.

    Downloads varps, varbits, and objects database if needed,
    then loads them into the respective resource modules.

    This should be called once at Client initialization.

    Returns:
        True if successful, False otherwise
    """
    global _resources_loaded

    if _resources_loaded:
        return True

    try:
        cache_manager = getCacheManager()
        cache_dir = cache_manager.getDataPath("game_data")
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Check if update needed
        if _needsUpdate(cache_dir):
            print("⬇️  Updating game resources...")
            base_url = f"{BASE_URL}/varps/latest"

            # Download all files
            files = {
                "metadata.json": "metadata.json",
                "varps.json": "varps.json",
                "varbits.json": "varbits.json",
                "objects.db": "objects.db.gz",  # Compressed
            }

            for local_name, remote_name in files.items():
                url = f"{base_url}/{remote_name}"
                dest = cache_dir / local_name
                decompress = remote_name.endswith(".gz")

                if not _downloadFile(url, dest, decompress_gz=decompress):
                    print(f"⚠️  Failed to download {local_name}")
                    return False

            print("✅ Resources downloaded successfully")

        # Load resources into modules
        from shadowlib._internal.resources import objects, varps

        # Load varps/varbits data
        varps_file = cache_dir / "varps.json"
        varbits_file = cache_dir / "varbits.json"

        with open(varps_file) as f:
            raw_varps = json.load(f)
            # Convert list to dict indexed by ID
            if isinstance(raw_varps, list):
                varps._varps_data = {item["id"]: item for item in raw_varps if "id" in item}
            else:
                varps._varps_data = raw_varps
            print(f"✅ Loaded {len(varps._varps_data)} varps")

        with open(varbits_file) as f:
            raw_varbits = json.load(f)
            # Convert list to dict indexed by ID
            if isinstance(raw_varbits, list):
                varps._varbits_data = {
                    item["id"]: item for item in raw_varbits if "id" in item
                }
            else:
                varps._varbits_data = raw_varbits
            print(f"✅ Loaded {len(varps._varbits_data)} varbits")

        # Load objects database
        import sqlite3

        db_file = cache_dir / "objects.db"
        objects._db_connection = sqlite3.connect(str(db_file))
        objects._db_connection.row_factory = sqlite3.Row
        print("✅ Loaded objects database")

        _resources_loaded = True
        return True

    except Exception as e:
        print(f"❌ Failed to load resources: {e}")
        import traceback

        traceback.print_exc()
        return False


# =============================================================================
# Generated Files Management (query proxies, constants, etc.)
# =============================================================================


def ensureGeneratedInPath() -> Path:
    """
    Ensure the generated cache directory is in sys.path for imports.

    Returns:
        Path to the generated directory
    """
    cache_manager = getCacheManager()
    generated_dir = cache_manager.generated_dir

    # Add to sys.path if not already there
    generated_str = str(generated_dir)
    if generated_str not in sys.path:
        sys.path.insert(0, generated_str)

    return generated_dir


def loadGeneratedModule(module_name: str) -> Any | None:
    """
    Load a generated module from cache.

    Args:
        module_name: Name of the module (e.g., 'query_proxies', 'constants')

    Returns:
        The loaded module, or None if it doesn't exist

    Example:
        >>> proxies = loadGeneratedModule('query_proxies')
        >>> if proxies:
        >>>     client = proxies.ClientProxy()
    """
    ensureGeneratedInPath()

    try:
        # Try to import the module
        import importlib

        return importlib.import_module(module_name)
    except ImportError:
        return None


def reloadGeneratedModule(module_name: str) -> Any | None:
    """
    Reload a generated module (useful after regeneration).

    Args:
        module_name: Name of the module (e.g., 'query_proxies', 'constants')

    Returns:
        The reloaded module, or None if it doesn't exist
    """
    ensureGeneratedInPath()

    try:
        import importlib

        if module_name in sys.modules:
            return importlib.reload(sys.modules[module_name])
        else:
            return importlib.import_module(module_name)
    except ImportError:
        return None


def hasGeneratedFiles() -> bool:
    """
    Check if generated files exist in cache.

    Returns:
        True if query_proxies.py and constants.py exist
    """
    cache_manager = getCacheManager()
    generated_dir = cache_manager.generated_dir

    proxy_file = generated_dir / "query_proxies.py"
    constants_file = generated_dir / "constants.py"

    return proxy_file.exists() and constants_file.exists()


def ensureGeneratedFiles():
    """
    Ensure generated files exist, triggering update if necessary.

    This should be called before importing generated modules.
    Raises FileNotFoundError if files can't be generated.
    """
    if not hasGeneratedFiles():
        print("⚠️  Generated files not found in cache, running updater...")
        try:
            from shadowlib._internal.updater.api import RuneLiteAPIUpdater

            updater = RuneLiteAPIUpdater()
            success = updater.update(force=False, max_age_days=7)

            if not success or not hasGeneratedFiles():
                raise FileNotFoundError(
                    "Failed to generate required files. "
                    "Run 'python -m shadowlib._internal.updater --force' manually."
                )
        except Exception as e:
            raise FileNotFoundError(
                f"Could not generate required files: {e}\n"
                f"Run 'python -m shadowlib._internal.updater --force' manually."
            ) from e


# Initialize on import - ensure generated path is available
ensureGeneratedInPath()
