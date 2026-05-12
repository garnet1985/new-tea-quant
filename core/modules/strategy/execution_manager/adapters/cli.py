"""CLI 宿主：同步阻塞执行至结束；与 BFF 共用 ``plan`` + ``execute``。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.modules.strategy.execution_manager.execution import execute_workbench_plan_sync
from core.modules.strategy.execution_manager.planning import plan_workbench_substeps
from core.modules.strategy.execution_manager.types import ProgressSink, WorkbenchExecutionResult

logger = logging.getLogger(__name__)

__all__ = [
    "run_workbench_step_via_cli_contract",
]


class _CliVerboseProgressSink:
    """可选：将整体进度打到 logger / 终端。"""

    __slots__ = ("_verbose",)

    def __init__(self, *, verbose: bool) -> None:
        self._verbose = bool(verbose)

    def on_overall_pct(self, pct: float) -> None:
        if self._verbose:
            logger.info("workbench step progress %.1f%%", pct)

    def on_substep_start(self, substep: str, index: int, total: int) -> None:
        if self._verbose:
            logger.info("substep %s (%s/%s)", substep, index + 1, total)

    def on_flow_progress(self, substep: str, flow_pct: float) -> None:
        if self._verbose:
            logger.debug("flow %s local %.1f%%", substep, flow_pct)


def run_workbench_step_via_cli_contract(
    *,
    strategy_name: str,
    step: str,
    api_settings: Dict[str, Any],
    is_force: bool,
    verbose: bool = False,
    engine_verbose: bool = False,
    stock_count: Optional[int] = None,
) -> WorkbenchExecutionResult:
    """
    阻塞执行工作台语义的一步（enum / price / capital）。

    ``api_settings`` 与 BFF POST body 的 ``settings`` 同源（通常为策略 ``settings.py`` 的 dict）。
    ``stock_count`` 仅对子步骤 ``enum`` 生效（CLI 测试采样）；其余步骤忽略。
    ``engine_verbose`` 传给 price/capital 的 ``Flow``（与 ``start-cli --verbose`` 对齐）。
    """
    from core.modules.strategy.services.launcher import workbench_step_run as wsr

    norm = wsr.normalize_step(step)
    if norm is None:
        raise ValueError(f"step 须为 enum / price / capital，收到 {step!r}")

    name = str(strategy_name or "").strip()
    if not name:
        raise ValueError("strategy_name 无效")

    discovered, err = wsr._resolve_discovered(name, api_settings)
    if err or discovered is None:
        raise ValueError(err or "无法解析策略")

    plan = plan_workbench_substeps(
        norm_step=norm,
        is_force=is_force,
        strategy_name=name,
        discovered=discovered,
    )
    progress: Optional[ProgressSink] = (
        _CliVerboseProgressSink(verbose=verbose) if verbose else None
    )
    return execute_workbench_plan_sync(
        strategy_name=name,
        user_facing_step=norm,
        discovered=discovered,
        plan=plan,
        job_id="cli-sync",
        progress=progress,
        enum_stock_count=stock_count,
        is_verbose=engine_verbose,
    )
