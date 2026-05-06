#!/usr/bin/env python3
"""Shared runtime helpers for loading strategy artifacts."""

from __future__ import annotations

import importlib
import inspect
from typing import TYPE_CHECKING, Optional, Tuple, Type

from core.infra.project_context import PathManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)

if TYPE_CHECKING:
    from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


def load_strategy_info(strategy_name: str) -> Optional["DiscoveredStrategy"]:
    from core.modules.strategy.services.discovery import StrategyDiscoveryHelper

    folder = PathManager.userspace() / "strategies" / strategy_name
    if not folder.is_dir():
        return None
    return StrategyDiscoveryHelper.load_strategy(folder)


def load_strategy_settings_view(
    strategy_name: str,
    *,
    strategy_info: Optional["DiscoveredStrategy"] = None,
) -> StrategySettingsView:
    if strategy_info is not None:
        return StrategySettingsView.from_dict(strategy_info.settings.to_dict())
    module = importlib.import_module(f"userspace.strategies.{strategy_name}.settings")
    settings = getattr(module, "settings", None)
    if not isinstance(settings, dict):
        raise ValueError(f"invalid settings for strategy: {strategy_name}")
    return StrategySettingsView.from_dict(settings)


def resolve_worker_class(
    strategy_name: str,
    *,
    worker_module_path: Optional[str] = None,
    worker_class_name: Optional[str] = None,
) -> Type[BaseStrategyWorker]:
    from core.modules.strategy.base_strategy_worker import BaseStrategyWorker

    if worker_module_path and worker_class_name:
        module = importlib.import_module(worker_module_path)
        worker_class = getattr(module, worker_class_name, None)
        if (
            isinstance(worker_class, type)
            and issubclass(worker_class, BaseStrategyWorker)
            and worker_class is not BaseStrategyWorker
        ):
            return worker_class

    module = importlib.import_module(f"userspace.strategies.{strategy_name}.strategy_worker")
    if hasattr(module, "StrategyWorker"):
        cls = getattr(module, "StrategyWorker")
        if isinstance(cls, type) and issubclass(cls, BaseStrategyWorker):
            return cls
    named = f"{strategy_name.capitalize()}StrategyWorker"
    if hasattr(module, named):
        cls = getattr(module, named)
        if isinstance(cls, type) and issubclass(cls, BaseStrategyWorker):
            return cls
    for _, obj in inspect.getmembers(module):
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseStrategyWorker)
            and obj is not BaseStrategyWorker
        ):
            return obj
    raise ValueError(f"strategy class not found: {strategy_name}")


def resolve_worker_ref(
    strategy_name: str,
    *,
    strategy_info: Optional["DiscoveredStrategy"] = None,
) -> Tuple[str, str]:
    if strategy_info is not None:
        return strategy_info.worker_module_path, strategy_info.worker_class_name
    worker_class = resolve_worker_class(strategy_name)
    return worker_class.__module__, worker_class.__name__


__all__ = [
    "load_strategy_info",
    "load_strategy_settings_view",
    "resolve_worker_class",
    "resolve_worker_ref",
]
