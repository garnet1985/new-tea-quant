#!/usr/bin/env python3
"""Shared runtime helpers for loading strategy artifacts."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type

from core.infra.project_context import ProjectContext
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.market_profile_id import (
    resolve_market_profile_id,
)
from core.modules.strategy.services.discovery.worker_loader import import_hooks_class
from core.modules.strategy.services.package.settings_loader import load_settings_dict_from_folder

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )
    from core.modules.strategy.hooks import StrategyHooks


def load_strategy_info(strategy_name: str) -> Optional["DiscoveredStrategy"]:
    from core.modules.strategy.services.discovery import StrategyDiscoveryHelper

    folder = ProjectContext.path.get_strategy_directory(strategy_name)
    if not folder.is_dir():
        return None
    return StrategyDiscoveryHelper.load_strategy(folder)


def load_strategy_settings_view(
    strategy_name: str,
    *,
    strategy_info: Optional["DiscoveredStrategy"] = None,
) -> StrategySettingsView:
    """加载并完整校验 ``StrategySettings``（含 market_profile / simulation / capital 等）。"""
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
        StrategySettings,
    )

    if strategy_info is not None:
        raw = strategy_info.settings.to_dict()
    else:
        folder = ProjectContext.path.get_strategy_directory(strategy_name)
        raw = load_settings_dict_from_folder(folder, strategy_key=strategy_name)
    validated = StrategySettings(raw_settings=dict(raw))
    validated.apply_defaults()
    report = validated.validate()
    report.raise_if_critical()
    return StrategySettingsView.from_dict(validated.to_dict())


def resolve_hooks_class(
    strategy_name: str,
    *,
    worker_module_path: Optional[str] = None,
    worker_class_name: Optional[str] = None,
    worker_file_path: Optional[str] = None,
    strategy_info: Optional["DiscoveredStrategy"] = None,
) -> Type["StrategyHooks"]:
    if strategy_info is not None:
        return import_hooks_class(
            worker_module_path=strategy_info.worker_module_path,
            worker_class_name=strategy_info.worker_class_name,
            worker_file_path=str(strategy_info.worker_file_path),
        )

    if worker_module_path and worker_class_name:
        file_path = worker_file_path
        if not file_path:
            file_path = str(ProjectContext.path.get_strategy_directory(strategy_name) / "strategy.py")
        return import_hooks_class(
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_file_path=str(file_path or ""),
        )

    info = load_strategy_info(strategy_name)
    if info is None:
        raise ValueError(f"strategy not found: {strategy_name}")
    return import_hooks_class(
        worker_module_path=info.worker_module_path,
        worker_class_name=info.worker_class_name,
        worker_file_path=str(info.worker_file_path),
    )


def resolve_worker_ref(
    strategy_name: str,
    *,
    strategy_info: Optional["DiscoveredStrategy"] = None,
) -> Tuple[str, str, str]:
    if strategy_info is not None:
        return (
            strategy_info.worker_module_path,
            strategy_info.worker_class_name,
            str(strategy_info.worker_file_path),
        )
    info = load_strategy_info(strategy_name)
    if info is None:
        hooks_class = resolve_hooks_class(strategy_name)
        source = inspect.getsourcefile(hooks_class) or ""
        return hooks_class.__module__, hooks_class.__name__, source
    return (
        info.worker_module_path,
        info.worker_class_name,
        str(info.worker_file_path),
    )


__all__ = [
    "load_strategy_info",
    "load_strategy_settings_view",
    "resolve_hooks_class",
    "resolve_market_profile_id",
    "resolve_worker_ref",
]
