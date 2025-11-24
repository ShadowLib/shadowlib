#!/usr/bin/env python3
"""
Custom naming convention checker for shadowlib.

Enforces camelCase for function names (e.g., getFoo, doSomething)
while allowing PascalCase for classes and UPPER_CASE for constants.
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


def isCamelCase(name: str) -> bool:
    """
    Check if a name follows camelCase convention.

    Args:
        name: The name to check

    Returns:
        bool: True if name is camelCase, False otherwise
    """
    # Allow special methods (dunder methods)
    if name.startswith("__") and name.endswith("__"):
        return True

    # Allow private methods (single underscore prefix) - can be snake_case
    if name.startswith("_") and not name.startswith("__"):
        # Private functions/methods can use snake_case
        return True

    # camelCase pattern: starts with lowercase, may contain uppercase letters
    # but not consecutive uppercase (to avoid UPPER_CASE)
    camel_case_pattern = r"^[a-z][a-zA-Z0-9]*$"
    return bool(re.match(camel_case_pattern, name))


def isPascalCase(name: str) -> bool:
    """
    Check if a name follows PascalCase convention.

    Args:
        name: The name to check

    Returns:
        bool: True if name is PascalCase, False otherwise
    """
    pascal_case_pattern = r"^[A-Z][a-zA-Z0-9]*$"
    return bool(re.match(pascal_case_pattern, name))


def isUpperCase(name: str) -> bool:
    """
    Check if a name follows UPPER_CASE convention.

    Args:
        name: The name to check

    Returns:
        bool: True if name is UPPER_CASE, False otherwise
    """
    upper_case_pattern = r"^[A-Z][A-Z0-9_]*$"
    return bool(re.match(upper_case_pattern, name))


class NamingChecker(ast.NodeVisitor):
    """AST visitor to check naming conventions."""

    def __init__(self, filename: str) -> None:
        """
        Initialize the naming checker.

        Args:
            filename: Path to the file being checked
        """
        self.filename = filename
        self.errors: List[Tuple[int, str]] = []

    def _isProperty(self, node: ast.FunctionDef) -> bool:
        """
        Check if a function has @property decorator.

        Properties are allowed to use PascalCase (for constants) or snake_case
        for better IDE autocomplete and to match attribute naming.
        Examples: ItemID, ObjectID, event_cache
        """
        return any(
            (isinstance(dec, ast.Name) and dec.id == "property") for dec in node.decorator_list
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions and check naming."""
        # Allow any naming for @property decorators (PascalCase, snake_case, camelCase)
        if self._isProperty(node):
            self.generic_visit(node)
            return

        if not isCamelCase(node.name):
            self.errors.append(
                (
                    node.lineno,
                    f"Function '{node.name}' should be camelCase "
                    f"(e.g., '{self._suggestCamelCase(node.name)}')",
                )
            )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions and check naming."""
        if not isCamelCase(node.name):
            self.errors.append(
                (
                    node.lineno,
                    f"Async function '{node.name}' should be camelCase "
                    f"(e.g., '{self._suggestCamelCase(node.name)}')",
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions and check naming."""
        # Allow private classes (leading underscore)
        name_to_check = node.name.lstrip("_")

        if name_to_check and not isPascalCase(name_to_check):
            self.errors.append(
                (
                    node.lineno,
                    f"Class '{node.name}' should be PascalCase "
                    f"(e.g., '{self._suggestPascalCase(node.name)}')",
                )
            )
        self.generic_visit(node)

    def _suggestCamelCase(self, name: str) -> str:
        """
        Suggest a camelCase version of a name.

        Args:
            name: The original name

        Returns:
            str: Suggested camelCase name
        """
        # Handle snake_case conversion
        parts = name.split("_")
        if len(parts) > 1:
            return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

        # If already one word, just lowercase first letter
        if name:
            return name[0].lower() + name[1:]
        return name

    def _suggestPascalCase(self, name: str) -> str:
        """
        Suggest a PascalCase version of a name.

        Args:
            name: The original name

        Returns:
            str: Suggested PascalCase name
        """
        # Handle snake_case conversion
        parts = name.split("_")
        if len(parts) > 1:
            return "".join(p.capitalize() for p in parts)

        # If already one word, just uppercase first letter
        if name:
            return name[0].upper() + name[1:]
        return name


def checkFile(filepath: Path) -> List[Tuple[int, str]]:
    """
    Check a Python file for naming convention violations.

    Args:
        filepath: Path to the Python file

    Returns:
        List[Tuple[int, str]]: List of (line_number, error_message) tuples
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        checker = NamingChecker(str(filepath))
        checker.visit(tree)
        return checker.errors
    except SyntaxError as e:
        return [(e.lineno or 0, f"Syntax error: {e.msg}")]
    except Exception as e:
        return [(0, f"Error parsing file: {e}")]


def main() -> int:
    """
    Main entry point for the naming checker.

    Returns:
        int: Exit code (0 for success, 1 for failures)
    """
    # Get all Python files in shadowlib directory
    shadowlib_dir = Path(__file__).parent.parent / "shadowlib"

    if not shadowlib_dir.exists():
        print(f"Error: {shadowlib_dir} does not exist")
        return 1

    python_files = list(shadowlib_dir.rglob("*.py"))

    if not python_files:
        print("No Python files found in shadowlib/")
        return 0

    # Exclude patterns (generated code only)
    exclude_patterns = [
        "/generated/",
    ]

    total_errors = 0
    for filepath in sorted(python_files):
        # Skip excluded files
        filepath_str = str(filepath)
        if any(pattern in filepath_str for pattern in exclude_patterns):
            continue

        errors = checkFile(filepath)
        if errors:
            print(f"\n{filepath}:")
            for lineno, message in errors:
                print(f"  Line {lineno}: {message}")
                total_errors += 1

    if total_errors > 0:
        print(f"\n❌ Found {total_errors} naming convention error(s)")
        return 1
    else:
        print("✅ All files follow the naming conventions!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
