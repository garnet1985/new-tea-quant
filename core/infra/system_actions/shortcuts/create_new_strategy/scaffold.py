#!/usr/bin/env python3
"""从模板新建策略目录。"""

from __future__ import annotations

from pathlib import Path

from core.infra.project_context import ProjectContext

from core.infra.system_actions.shortcuts._shared import (
    ScaffoldResult,
    copy_template,
    enable_in_settings,
    inject_meta_key_in_settings_file,
    resolve_dest,
)
from core.modules.strategy.core.services.discovery.path_rules import StrategyPathRules

STRATEGY_TEMPLATE_REL = Path("_template") / "empty_strategy"


def scaffold_strategy(raw_path: str) -> ScaffoldResult:
    """复制 ``strategies/_template/empty_strategy/`` 到 ``strategies/<raw_path>/``。"""
    root = ProjectContext.path.get_strategies_root()
    dest, key = resolve_dest(
        root=root,
        raw_path=raw_path,
        path_validator=StrategyPathRules.is_machine_readable_path,
    )
    template = (root / STRATEGY_TEMPLATE_REL).resolve()
    copy_template(template=template, dest=dest)
    enable_in_settings(dest / "settings.py")
    inject_meta_key_in_settings_file(dest / "settings.py", key)
    return ScaffoldResult(kind="strategy", key=key, dest=dest)


__all__ = ["scaffold_strategy"]
