#!/usr/bin/env python3
"""Shared runtime helpers for loading strategy artifacts."""

from __future__ import annotations

import importlib
import inspect
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type

from core.infra.project_context import PathManager
from core.modules.market_profile.constants import DEFAULT_PROFILE_ID
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
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
    """加载并完整校验 ``StrategySettings``（含 market_profile / simulation / capital 等）。"""
    if strategy_info is not None:
        raw = strategy_info.settings.to_dict()
    else:
        module = importlib.import_module(f"userspace.strategies.{strategy_name}.settings")
        settings = getattr(module, "settings", None)
        if not isinstance(settings, dict):
            raise ValueError(f"invalid settings for strategy: {strategy_name}")
        raw = settings
    validated = StrategySettings(raw_settings=dict(raw))
    validated.apply_defaults()
    report = validated.validate()
    report.raise_if_critical()
    return StrategySettingsView.from_dict(validated.to_dict())


def resolve_market_profile_id(
    job_payload: Dict[str, Any],
    *,
    settings_market_profile: str = "",
) -> str:
    """Flow 注入 ``market_profile_id`` 优先；否则用 settings 根级字符串。"""
    pid = str((job_payload or {}).get("market_profile_id") or "").strip()
    if pid:
        return pid
    fallback = str(settings_market_profile or "").strip()
    return fallback or DEFAULT_PROFILE_ID


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
    "resolve_market_profile_id",
    "resolve_worker_class",
    "resolve_worker_ref",
]
