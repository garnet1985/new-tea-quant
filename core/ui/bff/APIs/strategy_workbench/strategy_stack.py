"""Defer heavy strategy / workbench imports until first API use.

BFF 注册蓝图时会 import ``routes``；若在此处直接拉起 DataManager 等重栈，
会在 DB / userspace 尚未就绪时失败。通过本模块在首次请求时再加载。

工作台 V2 能力均经 ``modules.strategy.core.bff_support``（不再依赖 strategy_legacy）。
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any, Optional

_stack: Optional[SimpleNamespace] = None
_init_lock = threading.Lock()


def _load_attrs() -> dict[str, Any]:
    from core.modules.strategy.core.bff_support import (
        StrategyCatalog,
        StrategySettingsOptions,
        WorkbenchApplySettings,
        WorkbenchCacheClear,
        WorkbenchReports,
        WorkbenchRunLauncher,
        WorkbenchSnapshots,
        WorkbenchStockDetail,
    )

    return {
        "fetch_discovered_strategies_page": (
            StrategyCatalog.fetch_discovered_strategies_page
        ),
        "items_capital_allocation_strategies": (
            StrategySettingsOptions.items_capital_allocation_strategies
        ),
        "items_sampling_strategies": StrategySettingsOptions.items_sampling_strategies,
        "items_simulation_templates": (
            StrategySettingsOptions.items_simulation_templates
        ),
        "items_skip_investment_when": (
            StrategySettingsOptions.items_skip_investment_when
        ),
        "items_market_profiles": StrategySettingsOptions.items_market_profiles,
        "fetch_latest_workbench_snapshot": WorkbenchSnapshots.fetch_latest,
        "fetch_workbench_by_version": WorkbenchSnapshots.fetch_by_version,
        "fetch_strategy_versions_dropdown": WorkbenchSnapshots.list_dropdown,
        "parse_version_id": WorkbenchSnapshots.parse_version_id,
        "workbench_latest_ui_flags": WorkbenchSnapshots.ui_flags,
        "submit_workbench_step_via_bff_contract": WorkbenchRunLauncher.submit,
        "get_run_progress": WorkbenchRunLauncher.get_run_progress,
        "get_step_progress": WorkbenchRunLauncher.get_step_progress,
        "normalize_step": WorkbenchRunLauncher.normalize_step,
        "build_step_report_message": WorkbenchReports.build_step_report,
        "build_step_report_ref_message": WorkbenchReports.build_step_report_ref,
        "build_stock_detail_message": WorkbenchStockDetail.build,
        "apply_workbench_snapshot_settings_to_userspace": WorkbenchApplySettings.apply,
        "clear_workbench_simulation_cache_all": WorkbenchCacheClear.clear_all,
        "clear_workbench_simulation_cache_by_version": (
            WorkbenchCacheClear.clear_by_version
        ),
    }


def get_strategy_workbench_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack
    with _init_lock:
        if _stack is not None:
            return _stack
        _stack = SimpleNamespace(**_load_attrs())
    return _stack
