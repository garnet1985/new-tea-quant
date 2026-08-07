"""Filename / directory rules skipped when collecting userspace artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import FrozenSet


class RuntimeExcludes:
    """收集制品时跳过的运行时 / 缓存目录与文件（无业务特判）。"""

    RUNTIME_DIR_NAMES: FrozenSet[str] = frozenset(
        {".ntq", "results", "cache", "output", ".cache"}
    )
    IGNORE_FILE_SUFFIXES: FrozenSet[str] = frozenset({".pyc", ".pyo"})
    IGNORE_FILE_NAMES: FrozenSet[str] = frozenset(
        {
            ".DS_Store",
            "Thumbs.db",
        }
    )
    IGNORE_DIR_NAMES: FrozenSet[str] = frozenset(
        {
            "__pycache__",
            ".pytest_cache",
            ".git",
            "node_modules",
            ".venv",
        }
    )

    @staticmethod
    def should_skip_dir(_dir_path: Path, name: str) -> bool:
        return (
            name in RuntimeExcludes.IGNORE_DIR_NAMES
            or name in RuntimeExcludes.RUNTIME_DIR_NAMES
        )

    @staticmethod
    def should_skip_file(file_path: Path) -> bool:
        if file_path.name in RuntimeExcludes.IGNORE_FILE_NAMES:
            return True
        if file_path.suffix.lower() in RuntimeExcludes.IGNORE_FILE_SUFFIXES:
            return True
        if file_path.name.endswith(".bak"):
            return True
        return False
