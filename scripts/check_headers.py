#!/usr/bin/env python3
"""Check that Python source files in src/ have a future import or module docstring."""

from __future__ import annotations

import sys
from pathlib import Path


def check_file(path: Path) -> bool:
    """Return True if the file has an acceptable header."""
    text = path.read_text()
    lines = text.splitlines()

    if not lines or len(lines) < 2:
        return True  # Empty/tiny files are fine

    if path.name == "__init__.py":
        return True

    if path.name == "py.typed":
        return True

    # Must start with docstring or future import within first 5 lines
    for line in lines[:5]:
        stripped = line.strip()
        if stripped.startswith(('"""', "from __future__")):
            return True

    return False


def main() -> int:
    """Check all Python files in src/."""
    failed = False
    for path in sorted(Path("src").rglob("*.py")):
        if not check_file(path):
            print(f"FAIL: {path} -- missing docstring or future import in header")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
