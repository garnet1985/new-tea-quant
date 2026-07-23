"""工作台步骤执行管理 — 按 ``plan`` 同步执行各子步骤（引擎调用）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

from .types import PlannedSubstep, ProgressSink, WorkbenchExecutionResult
from .workbench_flow_progress import WorkbenchFlowProgress

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )

__all__ = [
    "execute_workbench_plan_sync",
    "run_workbench_substep_for_snapshot",
]


def run_workbench_substep_for_snapshot(
    step: str,
    strategy_name: str,
    discovered: "DiscoveredStrategy",
    *,
    force_refresh: bool,
    job_id: str,
    on_step_progress: Optional[Callable[[float], None]] = None,
    workbench_progress: Optional[WorkbenchFlowProgress] = None,
    stock_count: Optional[int] = None,
    is_verbose: bool = False,
) -> Tuple[int, Any, Optional[bool]]:
    """
    执行单个子步骤（enum / price / capital）。

    返回 ``(version, last_payload, used_db_cache)``；``used_db_cache`` 仅对
    price/capital 有值，其余为 ``None``。
    """
    wp = workbench_progress
    if step == "enum":
        from core.modules.strategy.launcher.enumerator_runtime_service import (
            EnumeratorRuntimeService,
        )

        ctx = EnumeratorRuntimeService.build_context(
            strategy_name=strategy_name,
            strategy_info=discovered,
            raw_settings_override=discovered.settings.to_dict(),
            force_refresh=force_refresh,
            workbench_run_id=job_id,
            workbench_strategy_name=strategy_name,
            stock_count=stock_count,
        )
        payload = EnumeratorRuntimeService.run_enum(ctx, workbench_progress=wp)
        return int(ctx.flow.last_version or 0), payload, None

    if step == "price":
        from core.modules.strategy.engines.simulator.price_factor.price_factor_flow import (
            PriceFactorFlow,
        )

        flow = PriceFactorFlow(is_verbose=is_verbose, force_refresh=force_refresh)
        cb = on_step_progress if callable(on_step_progress) else None
        summary = flow.run(
            strategy_name,
            discovered,
            progress_callback=cb,
            workbench_progress=wp,
        )
        return (
            int(flow.last_version or 0),
            summary,
            bool(getattr(flow, "used_db_cache", False)),
        )

    if step == "capital":
        from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow import (
            CapitalAllocationFlow,
        )

        flow = CapitalAllocationFlow(is_verbose=is_verbose, force_refresh=force_refresh)
        cb = on_step_progress if callable(on_step_progress) else None
        summary = flow.run(
            strategy_name,
            discovered,
            progress_callback=cb,
            workbench_progress=wp,
        )
        return (
            int(flow.last_version or 0),
            summary,
            bool(getattr(flow, "used_db_cache", False)),
        )

    raise ValueError(f"未知 workbench 子步骤: {step!r}")


def execute_workbench_plan_sync(
    *,
    strategy_name: str,
    user_facing_step: str,
    discovered: "DiscoveredStrategy",
    plan: List[PlannedSubstep],
    job_id: str,
    progress: Optional[ProgressSink] = None,
    enum_stock_count: Optional[int] = None,
    is_verbose: bool = False,
) -> WorkbenchExecutionResult:
    """
    按 ``plan`` 顺序同步跑完；``user_facing_step`` 为 URL/面板上的步骤（与 ``job_id`` 进度键一致）。

    ``enum_stock_count`` 仅作用于子步骤 ``enum``（CLI 枚举测试股票数）；工作台不传即可。
    """
    _ = user_facing_step
    name = str(strategy_name).strip()
    jid = str(job_id).strip()
    n = max(len(plan), 1)
    version_int = 0
    last_payload: Any = None
    last_used: Optional[bool] = None
    for i, (sub, force_sub) in enumerate(plan):
        if progress is not None:
            progress.on_substep_start(sub, i, n)

        wp: Optional[WorkbenchFlowProgress] = None
        on_prog_cb: Optional[Callable[[float], None]] = None
        if progress is not None:

            def _on_stage(
                substep: str,
                stage: str,
                ratio: float,
                counters: Optional[dict] = None,
            ) -> None:
                progress.on_step_stage(substep, stage, ratio, counters)

            wp = WorkbenchFlowProgress(_on_stage, sub)
            on_prog_cb = wp

        version_int, payload, used = run_workbench_substep_for_snapshot(
            sub,
            name,
            discovered,
            force_refresh=bool(force_sub),
            job_id=jid,
            on_step_progress=on_prog_cb if sub in ("price", "capital") else None,
            workbench_progress=wp,
            stock_count=enum_stock_count if sub == "enum" else None,
            is_verbose=is_verbose,
        )
        version_int = int(version_int or 0)
        last_payload = payload
        if used is not None:
            last_used = used

        if progress is not None and wp is not None:
            wp.stage("report", 1.0)

        if progress is not None:
            fin = getattr(progress, "on_substep_finish", None)
            if callable(fin):
                fin(sub, i, n, version_int)

    return WorkbenchExecutionResult(
        version=version_int,
        last_payload=last_payload,
        used_db_cache=last_used,
    )
