"""BFF 宿主：建 job、起 daemon 线程、落盘进度；HTTP 快速返回 ``job_id``。"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict

from core.modules.strategy.execution_manager.execution import execute_workbench_plan_sync
from core.modules.strategy.execution_manager.planning import plan_workbench_substeps

logger = logging.getLogger(__name__)

__all__ = [
    "submit_workbench_step_via_bff_contract",
]


class _WorkbenchDiskProgressSink:
    """将执行进度写入工作台进度 JSON（实现 ``ProgressSink``）。"""

    __slots__ = ("_strategy_name", "_job_id", "_user_step")

    def __init__(self, strategy_name: str, job_id: str, user_facing_step: str) -> None:
        self._strategy_name = str(strategy_name).strip()
        self._job_id = str(job_id).strip()
        self._user_step = str(user_facing_step).strip()

    def on_overall_pct(self, pct: float) -> None:
        from core.modules.strategy.services.launcher import workbench_step_run as wsr

        wsr._disk_workbench_step_progress(
            self._strategy_name, self._job_id, self._user_step, pct
        )

    def on_substep_start(self, substep: str, index: int, total: int) -> None:
        pass

    def on_flow_progress(self, substep: str, flow_pct: float) -> None:
        pass


def _run_workbench_job_in_thread(
    job_id: str,
    strategy_name: str,
    norm_step: str,
    discovered: Any,
    is_force: bool,
) -> None:
    from core.modules.strategy.services.launcher import workbench_step_run as wsr

    wsr.job_update(job_id, status="running", progress=1.0)
    wsr._disk_mark_running(strategy_name, job_id, norm_step)
    try:
        wsr.job_update(job_id, progress=5.0)
        plan = plan_workbench_substeps(
            norm_step=norm_step,
            is_force=is_force,
            strategy_name=strategy_name,
            discovered=discovered,
        )
        sink = _WorkbenchDiskProgressSink(strategy_name, job_id, norm_step)
        result = execute_workbench_plan_sync(
            strategy_name=strategy_name,
            user_facing_step=norm_step,
            discovered=discovered,
            plan=plan,
            job_id=job_id,
            progress=sink,
            enum_stock_count=None,
            is_verbose=False,
        )
        sid_int = int(result.snapshot_id or 0)
        wsr.job_update(
            job_id,
            status="completed",
            progress=100.0,
            snapshot_id=sid_int,
        )
        wsr._merge_snapshot_into_disk_progress(strategy_name, job_id, norm_step, sid_int)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Workbench step run failed job_id=%s", job_id)
        wsr.job_update(job_id, status="failed", progress=100.0, error=str(exc))
        wsr._disk_mark_failed(strategy_name, job_id, norm_step, str(exc))


def submit_workbench_step_via_bff_contract(
    *,
    strategy_name: str,
    step: str,
    api_settings: Dict[str, Any],
    is_force: bool,
) -> Dict[str, Any]:
    """
    与 ``workbench_step_run.trigger_workbench_step_run`` 契约一致：

    - 成功：``{"is_triggered": True, "job_id": "<uuid>"}``
    - 失败：``{"is_triggered": False, "reason": "..."}``
    """
    from core.modules.strategy.services.launcher import workbench_step_run as wsr

    norm_step = wsr.normalize_step(step)
    if norm_step is None:
        return {
            "is_triggered": False,
            "reason": f"step 须为 enum / price / capital，收到 {step!r}",
        }

    name = str(strategy_name or "").strip()
    if not name:
        return {"is_triggered": False, "reason": "strategy_name 无效"}

    discovered, err = wsr._resolve_discovered(name, api_settings)
    if err or discovered is None:
        return {"is_triggered": False, "reason": err or "无法解析策略"}

    jid = wsr.job_create(strategy_name=name, step=norm_step, is_force=is_force)
    wsr._seed_workbench_progress_file(name, jid, norm_step)
    thread = threading.Thread(
        target=_run_workbench_job_in_thread,
        args=(jid, name, norm_step, discovered, is_force),
        daemon=True,
        name=f"workbench-run-{jid[:8]}",
    )
    thread.start()
    return {"is_triggered": True, "job_id": jid}
