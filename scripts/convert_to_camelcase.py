#!/usr/bin/env python3
"""
Convert all function names from snake_case to camelCase throughout the codebase.

This script:
1. Scans all Python files in shadowlib/
2. Identifies function definitions with snake_case names
3. Converts them to camelCase
4. Updates all calls to those functions throughout the codebase
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple


def snakeToCamel(snake_str: str) -> str:
    """
    Convert snake_case to camelCase.

    Args:
        snake_str: String in snake_case

    Returns:
        String in camelCase
    """
    # Handle private/protected methods (leading underscores)
    leading_underscores = len(snake_str) - len(snake_str.lstrip("_"))
    name_part = snake_str[leading_underscores:]

    # Handle dunder methods (don't convert)
    if name_part.startswith("__") and name_part.endswith("__"):
        return snake_str

    # Split by underscore and convert
    components = name_part.split("_")

    # Keep first component lowercase, capitalize rest
    camel = components[0].lower() + "".join(x.title() for x in components[1:])

    # Add back leading underscores
    return "_" * leading_underscores + camel


class FunctionNameCollector(ast.NodeVisitor):
    """Collect all function names that need conversion."""

    def __init__(self):
        self.functions: Dict[str, str] = {}  # old_name -> new_name

    def visit_FunctionDef(self, node):
        old_name = node.name

        # Skip dunder methods
        if old_name.startswith("__") and old_name.endswith("__"):
            self.generic_visit(node)
            return

        # Convert if it has underscores
        if "_" in old_name:
            new_name = snakeToCamel(old_name)
            if new_name != old_name:
                self.functions[old_name] = new_name

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        old_name = node.name

        # Skip dunder methods
        if old_name.startswith("__") and old_name.endswith("__"):
            self.generic_visit(node)
            return

        # Convert if it has underscores
        if "_" in old_name:
            new_name = snakeToCamel(old_name)
            if new_name != old_name:
                self.functions[old_name] = new_name

        self.generic_visit(node)


def collectAllFunctionNames(directory: Path) -> Dict[str, str]:
    """
    Scan all Python files and collect function names to convert.

    Args:
        directory: Root directory to scan

    Returns:
        Dict mapping old_name -> new_name
    """
    all_functions = {}

    for py_file in directory.rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(py_file))
            collector = FunctionNameCollector()
            collector.visit(tree)

            all_functions.update(collector.functions)

        except SyntaxError as e:
            print(f"⚠️  Syntax error in {py_file}: {e}")
        except Exception as e:
            print(f"⚠️  Error processing {py_file}: {e}")

    return all_functions


def replaceFunctionNames(filepath: Path, replacements: Dict[str, str]) -> Tuple[int, List[str]]:
    """
    Replace function names in a file.

    Args:
        filepath: Path to Python file
        replacements: Dict of old_name -> new_name

    Returns:
        Tuple of (number of replacements, list of changes)
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        changes = []

        # Sort by length (longest first) to avoid partial replacements
        sorted_replacements = sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True)

        for old_name, new_name in sorted_replacements:
            # Pattern to match function definitions and calls
            # Matches: def old_name(, self.old_name(, obj.old_name(, old_name(
            patterns = [
                (rf"\bdef {re.escape(old_name)}\b", f"def {new_name}"),
                (rf"\basync def {re.escape(old_name)}\b", f"async def {new_name}"),
                (rf"\.{re.escape(old_name)}\(", f".{new_name}("),
                (rf"\b{re.escape(old_name)}\(", f"{new_name}("),
                # Also match assignments like: some_func = other_func
                (rf"\b{re.escape(old_name)}\s*=\s*", f"{new_name} = "),
                # Match in decorators
                (rf"@{re.escape(old_name)}\b", f"@{new_name}"),
            ]

            for pattern, replacement in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    old_content = content
                    content = re.sub(pattern, replacement, content)
                    if content != old_content:
                        if old_name not in [c[0] for c in changes]:
                            changes.append((old_name, new_name, len(matches)))

        # Only write if changes were made
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return (len(changes), changes)

        return (0, [])

    except Exception as e:
        print(f"⚠️  Error processing {filepath}: {e}")
        return (0, [])


def main():
    """Main conversion process."""
    shadowlib_dir = Path(__file__).parent.parent / "shadowlib"

    if not shadowlib_dir.exists():
        print(f"❌ Error: {shadowlib_dir} not found")
        return 1

    print("🔍 Step 1: Collecting all function names...")
    print("=" * 70)

    function_map = collectAllFunctionNames(shadowlib_dir)

    if not function_map:
        print("✅ No snake_case functions found - all functions already camelCase!")
        return 0

    print(f"Found {len(function_map)} functions to convert:")
    for i, (old, new) in enumerate(sorted(function_map.items())[:20], 1):
        print(f"  {i}. {old} → {new}")

    if len(function_map) > 20:
        print(f"  ... and {len(function_map) - 20} more")

    print("\n" + "=" * 70)
    print("🔄 Step 2: Converting function names in all files...")
    print("=" * 70)

    python_files = list(shadowlib_dir.rglob("*.py"))
    total_files_changed = 0
    total_replacements = 0

    for filepath in sorted(python_files):
        num_changes, changes = replaceFunctionNames(filepath, function_map)

        if num_changes > 0:
            total_files_changed += 1
            total_replacements += sum(count for _, _, count in changes)

            print(f"\n📝 {filepath.relative_to(shadowlib_dir.parent)}:")
            for old_name, new_name, count in changes[:10]:  # Show first 10
                print(f"  ✓ {old_name} → {new_name} ({count} occurrences)")

            if len(changes) > 10:
                print(f"  ... and {len(changes) - 10} more changes")

    print("\n" + "=" * 70)
    print("✅ Conversion complete!")
    print(f"   - {len(function_map)} unique functions converted")
    print(f"   - {total_replacements} total replacements made")
    print(f"   - {total_files_changed} files modified")
    print("=" * 70)

    print("\n💡 Next steps:")
    print("   1. Run: python check_naming.py")
    print("   2. Run: python verify_setup.py")
    print("   3. Test imports: python -c 'import shadowlib'")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
