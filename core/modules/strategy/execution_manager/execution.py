"""工作台步骤执行管理 — 按 ``plan`` 同步执行各子步骤（引擎调用）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

from .types import PlannedSubstep, ProgressSink, WorkbenchExecutionResult

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
    is_force: bool,
    job_id: str,
    on_step_progress: Optional[Callable[[float], None]] = None,
    stock_count: Optional[int] = None,
    is_verbose: bool = False,
) -> Tuple[int, Any, Optional[bool]]:
    """
    执行单个子步骤（enum / price / capital）。

    返回 ``(last_snapshot_id, last_payload, used_db_cache)``；``used_db_cache`` 仅对
    price/capital 有值，其余为 ``None``。
    """
    if step == "enum":
        from core.modules.strategy.launcher.enumerator_runtime_service import (
            EnumeratorRuntimeService,
        )

        ctx = EnumeratorRuntimeService.build_context(
            strategy_name=strategy_name,
            strategy_info=discovered,
            raw_settings_override=discovered.settings.to_dict(),
            force_refresh=is_force,
            workbench_run_id=job_id,
            workbench_strategy_name=strategy_name,
            stock_count=stock_count,
        )
        payload = EnumeratorRuntimeService.run_enum(ctx)
        return int(ctx.flow.last_snapshot_id or 0), payload, None

    if step == "price":
        from core.modules.strategy.engines.simulator.price_factor.price_factor_flow import (
            PriceFactorFlow,
        )

        flow = PriceFactorFlow(is_verbose=is_verbose, force_refresh=is_force)
        cb = on_step_progress if callable(on_step_progress) else None
        summary = flow.run(strategy_name, discovered, progress_callback=cb)
        return (
            int(flow.last_snapshot_id or 0),
            summary,
            bool(getattr(flow, "last_run_used_db_cache", False)),
        )

    if step == "capital":
        from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow import (
            CapitalAllocationFlow,
        )

        flow = CapitalAllocationFlow(is_verbose=is_verbose, force_refresh=is_force)
        cb = on_step_progress if callable(on_step_progress) else None
        summary = flow.run(strategy_name, discovered, progress_callback=cb)
        return (
            int(flow.last_snapshot_id or 0),
            summary,
            bool(getattr(flow, "last_run_used_db_cache", False)),
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
    sid_int = 0
    last_payload: Any = None
    last_used: Optional[bool] = None
    for i, (sub, force_sub) in enumerate(plan):
        span = 85.0 / n
        base_pct = 5.0 + span * float(i)
        if progress is not None:
            progress.on_substep_start(sub, i, n)

        if sub in ("price", "capital") and progress is not None:

            def on_prog(
                p_local: float,
                *,
                _sub: str = sub,
                _i: int = i,
                _n: int = n,
            ) -> None:
                sp = 85.0 / _n
                b = 5.0 + sp * float(_i)
                v = min(94.0, b + sp * (float(p_local) / 100.0))
                progress.on_overall_pct(v)
                progress.on_flow_progress(_sub, float(p_local))

            on_prog_cb: Optional[Callable[[float], None]] = on_prog
        else:
            on_prog_cb = None

        sid_int, payload, used = run_workbench_substep_for_snapshot(
            sub,
            name,
            discovered,
            is_force=bool(force_sub),
            job_id=jid,
            on_step_progress=on_prog_cb if sub in ("price", "capital") else None,
            stock_count=enum_stock_count if sub == "enum" else None,
            is_verbose=is_verbose,
        )
        sid_int = int(sid_int or 0)
        last_payload = payload
        if used is not None:
            last_used = used

        if sub == "enum" and progress is not None:
            progress.on_overall_pct(min(94.0, base_pct + span * 0.92))

        if progress is not None:
            fin = getattr(progress, "on_substep_finish", None)
            if callable(fin):
                fin(sub, i, n, sid_int)

    return WorkbenchExecutionResult(
        snapshot_id=sid_int,
        last_payload=last_payload,
        last_used_db_cache=last_used,
    )
