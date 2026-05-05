"""userspace 策略目录与 ``settings.py`` 路径解析（与 discovery 约定一致）。"""

from __future__ import annotations

from pathlib import Path

from core.infra.project_context.path_manager import PathManager


def resolve_strategy_settings_path(strategy_name: str) -> Path:
    """``userspace/strategies/<strategy_name>/settings.py``。"""
    return PathManager.strategy_settings(str(strategy_name).strip())
