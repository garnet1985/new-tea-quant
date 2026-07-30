"""Lazy wiring to ``core.modules.strategy.launcher`` (remaining routes still on stack).

Loaded on first request so BFF startup does not pull DataManager.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any, Optional

_stack: Optional[SimpleNamespace] = None
_lock = threading.Lock()


def _load() -> dict[str, Any]:
    from core.modules.strategy.launcher import (
        StrategySettingsOptions,
        WorkbenchApplySettings,
        WorkbenchRunLauncher,
        WorkbenchSnapshots,
    )
    from core.modules.strategy.launcher.scanner_run import (
        get_scan_page_context,
        get_scan_progress,
        get_scan_readiness,
        trigger_strategy_scan_run,
    )

    return {
        # simulation options
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
        # snapshots
        "fetch_latest_workbench_snapshot": WorkbenchSnapshots.fetch_latest,
        "fetch_workbench_by_version": WorkbenchSnapshots.fetch_by_version,
        "fetch_strategy_versions_dropdown": WorkbenchSnapshots.list_dropdown,
        "parse_version_id": WorkbenchSnapshots.parse_version_id,
        "workbench_latest_ui_flags": WorkbenchSnapshots.ui_flags,
        # run
        "submit_workbench_step_via_bff_contract": WorkbenchRunLauncher.submit,
        "get_run_progress": WorkbenchRunLauncher.get_run_progress,
        "get_step_progress": WorkbenchRunLauncher.get_step_progress,
        "normalize_step": WorkbenchRunLauncher.normalize_step,
        # apply
        "apply_workbench_snapshot_settings_to_userspace": WorkbenchApplySettings.apply,
        # scan
        "get_scan_page_context": get_scan_page_context,
        "get_scan_progress": get_scan_progress,
        "get_scan_readiness": get_scan_readiness,
        "trigger_strategy_scan_run": trigger_strategy_scan_run,
    }


def get_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack
    with _lock:
        if _stack is not None:
            return _stack
        _stack = SimpleNamespace(**_load())
    return _stack
