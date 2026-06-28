"""Filename / directory rules skipped when collecting userspace artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import FrozenSet

# Align with devtools/quick_tools/package_init_userspace.py (rules only, no devtools import).
RUNTIME_DIR_NAMES: FrozenSet[str] = frozenset({".ntq", "results", "cache", "output", ".cache"})

IGNORE_FILE_SUFFIXES: FrozenSet[str] = frozenset({".pyc", ".pyo"})
IGNORE_FILE_NAMES: FrozenSet[str] = frozenset({
    ".DS_Store",
    "Thumbs.db",
})
IGNORE_DIR_NAMES: FrozenSet[str] = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".git",
    "node_modules",
    ".venv",
})


def should_skip_dir(dir_path: Path, name: str) -> bool:
    if name in IGNORE_DIR_NAMES or name in RUNTIME_DIR_NAMES:
        return True
    if name == "results" and "strategies" in dir_path.parts:
        return True
    parts = dir_path.parts
    if "extensions" in parts and "tags" in parts and name in RUNTIME_DIR_NAMES - {".ntq"}:
        return True
    return False


def should_skip_file(file_path: Path) -> bool:
    if file_path.name in IGNORE_FILE_NAMES:
        return True
    if file_path.suffix.lower() in IGNORE_FILE_SUFFIXES:
        return True
    if file_path.name.endswith(".bak"):
        return True
    return False