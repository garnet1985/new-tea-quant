"""Reveal a strategy folder in the OS file manager (local BFF only)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from core.infra.project_context import ProjectContext
from core.modules.strategy import Strategy


def _ensure_under_strategies(folder: Path) -> Path:
    root = ProjectContext.path.get_strategies_root().resolve()
    resolved = Path(folder).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("策略目录不在 userspace/strategies 下") from exc
    if not resolved.is_dir():
        raise FileNotFoundError("策略文件夹不存在")
    return resolved


def reveal_directory(folder: Path) -> None:
    path = str(folder)
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=True, timeout=15)
        return
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    subprocess.run(["xdg-open", path], check=True, timeout=15)


class StrategyFolderImplementer:
    def lazy_load(self) -> "StrategyFolderImplementer":
        return self

    def reveal(self, strategy_key_or_name: str) -> Dict[str, Any]:
        folder = _ensure_under_strategies(Strategy.resolve_folder(strategy_key_or_name))
        reveal_directory(folder)
        return {
            "opened": True,
            "path": str(folder),
        }


impl = StrategyFolderImplementer()
