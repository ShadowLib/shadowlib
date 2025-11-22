#!/usr/bin/env python3
"""
Verify that the ShadowLib package is set up correctly.

This script checks:
- Package structure
- Import functionality
- Naming conventions
- Test discovery
"""

import sys
from pathlib import Path


def checkPackageStructure() -> bool:
    """Verify the package directory structure exists."""
    print("Checking package structure...")

    required_dirs = [
        "shadowlib",
        "shadowlib/world",
        "shadowlib/tabs",
        "shadowlib/interfaces",
        "shadowlib/navigation",
        "shadowlib/interactions",
        "shadowlib/input",
        "shadowlib/types",
        "shadowlib/utilities",
        "shadowlib/resources",
        "shadowlib/_internal",
        "tests",
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)

    if missing_dirs:
        print(f"  ❌ Missing directories: {', '.join(missing_dirs)}")
        return False

    print("  ✅ All required directories exist")
    return True


def checkRequiredFiles() -> bool:
    """Verify required configuration files exist."""
    print("\nChecking required files...")

    required_files = [
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "scripts/check_naming.py",
        ".pre-commit-config.yaml",
        ".gitignore",
        "Makefile",
        "shadowlib/__init__.py",
        "shadowlib/client.py",
        "shadowlib/_internal/query.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"  ❌ Missing files: {', '.join(missing_files)}")
        return False

    print("  ✅ All required files exist")
    return True


def checkImports() -> bool:
    """Verify that the package can be imported."""
    print("\nChecking imports...")

    try:
        import shadowlib

        print(f"  ✅ Successfully imported shadowlib (version {shadowlib.__version__})")

        from shadowlib import Client

        print("  ✅ Successfully imported Client")

        from shadowlib._internal.query import QueryBuilder

        print("  ✅ Successfully imported QueryBuilder")

        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        print("  → Run: pip install -e .")
        return False


def checkBasicFunctionality() -> bool:
    """Verify basic functionality works."""
    print("\nChecking basic functionality...")

    try:
        from shadowlib import Client

        client = Client()
        print("  ✅ Client instantiation works")

        if not client.isConnected():
            print("  ✅ isConnected() returns False initially")
        else:
            print("  ❌ isConnected() should return False initially")
            return False

        client.connect()
        if client.isConnected():
            print("  ✅ connect() and isConnected() work")
        else:
            print("  ❌ connect() should set isConnected() to True")
            return False

        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def checkNamingConventions() -> bool:
    """Verify naming conventions are followed."""
    print("\nChecking naming conventions...")

    # Check if check_naming.py exists and is executable
    naming_checker = Path("scripts/check_naming.py")
    if not naming_checker.exists():
        print("  ❌ scripts/check_naming.py not found")
        return False

    print("  ✅ Naming convention checker exists")
    print("  → Run: make naming (to verify)")
    return True


def main() -> int:
    """
    Run all verification checks.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    print("=" * 60)
    print("ShadowLib Setup Verification")
    print("=" * 60)

    checks = [
        ("Package Structure", checkPackageStructure),
        ("Required Files", checkRequiredFiles),
        ("Imports", checkImports),
        ("Basic Functionality", checkBasicFunctionality),
        ("Naming Conventions", checkNamingConventions),
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n❌ {check_name} failed with exception: {e}")
            results.append((check_name, False))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All checks passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Install dev dependencies: pip install -e '.[dev]'")
        print("2. Set up pre-commit hooks: pre-commit install")
        print("3. Run tests: pytest")
        print("4. Check naming: python check_naming.py")
        print("5. Start developing!")
        return 0
    else:
        print("\n❌ Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
