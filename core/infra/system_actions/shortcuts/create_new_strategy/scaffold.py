#!/usr/bin/env python3
"""从模板新建策略目录。"""

from __future__ import annotations

from pathlib import Path

from core.infra.project_context import PathManager
from core.infra.system_actions.shortcuts._shared import (
    ScaffoldResult,
    copy_template,
    enable_in_settings,
    resolve_dest,
)
from core.modules.strategy.services.discovery.path_rules import is_machine_readable_strategy_path

STRATEGY_TEMPLATE_REL = Path("_template") / "empty_strategy"


def scaffold_strategy(raw_path: str) -> ScaffoldResult:
    """复制 ``strategies/_template/empty_strategy/`` 到 ``strategies/<raw_path>/``。"""
    root = PathManager.get_strategies_root()
    dest, key = resolve_dest(
        root=root,
        raw_path=raw_path,
        path_validator=is_machine_readable_strategy_path,
    )
    template = (root / STRATEGY_TEMPLATE_REL).resolve()
    copy_template(template=template, dest=dest)
    enable_in_settings(dest / "settings.py")
    return ScaffoldResult(kind="strategy", key=key, dest=dest)


__all__ = ["scaffold_strategy"]
