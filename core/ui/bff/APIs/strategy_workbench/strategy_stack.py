"""Defer heavy strategy / workbench imports until first API use.

BFF 注册蓝图时会 import ``routes``；若在此处直接 ``from core.modules...workbench``，
会在 DB / userspace 尚未就绪时拉起 ``DataManager`` 等重栈。通过本模块在首次请求时再加载。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

_stack: Optional[SimpleNamespace] = None


def get_strategy_workbench_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack
    from core.modules.strategy.launcher import fetch_latest_workbench_snapshot
    from core.modules.strategy.launcher.workbench import (
        apply_workbench_snapshot_settings_to_userspace,
        build_step_report_message,
        build_step_report_ref_message,
        fetch_workbench_snapshot_by_snapshot_id,
        parse_snapshot_id,
        workbench_latest_ui_flags,
    )
    from core.modules.strategy.launcher.workbench_catalog import (
        fetch_discovered_strategies_page,
        fetch_strategy_versions_dropdown,
        items_capital_allocation_strategies,
        items_sampling_strategies,
    )
    from core.modules.strategy.execution_manager import (
        get_run_progress,
        get_step_progress,
        normalize_step,
        submit_workbench_step_via_bff_contract,
    )

    _stack = SimpleNamespace(
        fetch_latest_workbench_snapshot=fetch_latest_workbench_snapshot,
        apply_workbench_snapshot_settings_to_userspace=apply_workbench_snapshot_settings_to_userspace,
        build_step_report_message=build_step_report_message,
        build_step_report_ref_message=build_step_report_ref_message,
        fetch_workbench_snapshot_by_snapshot_id=fetch_workbench_snapshot_by_snapshot_id,
        parse_snapshot_id=parse_snapshot_id,
        workbench_latest_ui_flags=workbench_latest_ui_flags,
        fetch_discovered_strategies_page=fetch_discovered_strategies_page,
        fetch_strategy_versions_dropdown=fetch_strategy_versions_dropdown,
        items_capital_allocation_strategies=items_capital_allocation_strategies,
        items_sampling_strategies=items_sampling_strategies,
        get_run_progress=get_run_progress,
        get_step_progress=get_step_progress,
        normalize_step=normalize_step,
        submit_workbench_step_via_bff_contract=submit_workbench_step_via_bff_contract,
    )
    return _stack
