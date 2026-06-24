"""BFF 宿主：建 job、起 daemon 线程、落盘进度；HTTP 快速返回 ``job_id``。"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from ..execution import execute_workbench_plan_sync
from ..planning import plan_workbench_substeps
from ..workbench_disk_progress import (
    disk_mark_failed,
    disk_mark_running,
    disk_workbench_step_progress,
    merge_version_into_disk_progress,
    seed_workbench_progress_file,
)
from ..workbench_jobs import job_create, job_update
from ..workbench_resolve import (
    normalize_step,
    resolve_discovered_strategy,
)
from ..workbench_run_envelope import (
    get_run_progress,
    run_envelope_apply_step_stage,
    run_envelope_fail,
    run_envelope_mark_phase_completed,
    run_envelope_mark_started,
    run_envelope_on_substep_finish,
    run_envelope_on_substep_start,
    seed_workbench_run_envelope,
)

logger = logging.getLogger(__name__)

_active_workbench_jobs: Dict[str, threading.Thread] = {}
_workbench_jobs_lock = threading.Lock()


def _workbench_duckdb_prepare_for_run() -> None:
    try:
        from core.infra.db.engines.duckdb.process_pool_scope import (
            is_duckdb_backend,
            recover_after_worker_pool_interrupt,
        )

        if is_duckdb_backend():
            recover_after_worker_pool_interrupt()
    except Exception as exc:
        logger.warning("Workbench DuckDB 启动前收尾: %s", exc)


def _workbench_duckdb_finalize_after_run() -> None:
    try:
        from core.infra.db.engines.duckdb.process_pool_scope import (
            ensure_data_manager_restored,
            is_duckdb_backend,
            wait_pool_children_done,
        )

        if not is_duckdb_backend():
            return
        wait_pool_children_done(timeout_sec=30.0)
        ensure_data_manager_restored()
    except Exception as exc:
        logger.warning("Workbench DuckDB 结束后恢复: %s", exc)


__all__ = [
    "submit_workbench_step_via_bff_contract",
]


class _WorkbenchRunProgressSink:
    """编排信封 + 兼容旧版按 URL step 单文件进度。"""

    __slots__ = ("_strategy_name", "_job_id", "_user_step", "_last_idx")

    def __init__(self, strategy_name: str, job_id: str, user_facing_step: str) -> None:
        self._strategy_name = str(strategy_name).strip()
        self._job_id = str(job_id).strip()
        self._user_step = str(user_facing_step).strip()
        self._last_idx = 0

    def on_overall_pct(self, pct: float) -> None:
        pass

    def on_substep_start(self, substep: str, index: int, total: int) -> None:
        self._last_idx = int(index)
        run_envelope_on_substep_start(
            self._strategy_name,
            self._job_id,
            index,
            total,
            substep,
        )
        self.on_step_stage(substep, "load", 0.0)

    def on_step_stage(
        self,
        substep: str,
        stage: str,
        stage_ratio: float = 0.0,
        counters: Optional[Dict[str, Any]] = None,
    ) -> None:
        run_envelope_apply_step_stage(
            self._strategy_name,
            self._job_id,
            substep,
            stage,
            stage_ratio,
            counters=counters,
        )
        self._sync_legacy_disk_pct()

    def on_flow_progress(self, substep: str, flow_pct: float) -> None:
        try:
            fp = float(flow_pct)
        except (TypeError, ValueError):
            fp = 0.0
        self.on_step_stage(substep, "execute", fp / 100.0)

    def on_substep_finish(
        self, substep: str, index: int, total: int, version: int
    ) -> None:
        run_envelope_on_substep_finish(
            self._strategy_name,
            self._job_id,
            index,
            total,
            substep,
            int(version or 0),
        )
        self._sync_legacy_disk_pct()


def _run_workbench_job_in_thread(
    job_id: str,
    strategy_name: str,
    norm_step: str,
    discovered: Any,
    force_refresh: bool,
) -> None:
    sink: Optional[_WorkbenchRunProgressSink] = None
    job_update(job_id, status="running", progress=1.0)
    disk_mark_running(strategy_name, job_id, norm_step)
    _workbench_duckdb_prepare_for_run()
    try:
        plan = plan_workbench_substeps(
            norm_step=norm_step,
            force_refresh=force_refresh,
            strategy_name=strategy_name,
            discovered=discovered,
        )
        sink = _WorkbenchRunProgressSink(strategy_name, job_id, norm_step)
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
        ver_int = int(result.version or 0)
        job_update(
            job_id,
            status="completed",
            progress=100.0,
            version=ver_int,
        )
        merge_version_into_disk_progress(strategy_name, job_id, norm_step, ver_int)
        run_envelope_mark_phase_completed(strategy_name, job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Workbench step run failed job_id=%s", job_id)
        job_update(job_id, status="failed", progress=100.0, error=str(exc))
        fail_idx = int(getattr(sink, "_last_idx", 0) or 0) if sink is not None else 0
        run_envelope_fail(strategy_name, job_id, fail_idx, str(exc))
        disk_mark_failed(strategy_name, job_id, norm_step, str(exc))
    finally:
        _workbench_duckdb_finalize_after_run()
        with _workbench_jobs_lock:
            if _active_workbench_jobs.get(strategy_name) is threading.current_thread():
                _active_workbench_jobs.pop(strategy_name, None)


def submit_workbench_step_via_bff_contract(
    *,
    strategy_name: str,
    step: str,
    api_settings: Dict[str, Any],
    force_refresh: bool,
) -> Dict[str, Any]:
    """
    BFF 触发异步工作台一步。

    - 成功：``{"is_triggered": True, "job_id": "<uuid>", "run_id": "...", "steps": [...]}``
    - 失败：``{"is_triggered": False, "reason": "..."}``
    """
    norm_step = normalize_step(step)
    if norm_step is None:
        return {
            "is_triggered": False,
            "reason": f"step 须为 enum / price / capital，收到 {step!r}",
        }

    name = str(strategy_name or "").strip()
    if not name:
        return {"is_triggered": False, "reason": "strategy_name 无效"}

    discovered, err = resolve_discovered_strategy(name, api_settings)
    if err or discovered is None:
        return {"is_triggered": False, "reason": err or "无法解析策略"}

    plan: List[Tuple[str, bool]] = plan_workbench_substeps(
        norm_step=norm_step,
        force_refresh=force_refresh,
        strategy_name=name,
        discovered=discovered,
    )

    jid = job_create(strategy_name=name, step=norm_step, force_refresh=force_refresh)
    seed_workbench_progress_file(name, jid, norm_step)
    steps_payload = seed_workbench_run_envelope(name, jid, plan)
    run_envelope_mark_started(name, jid)
    packed = get_run_progress(strategy_name=name, job_id=jid)
    if packed and isinstance(packed.get("steps"), list):
        steps_payload = packed["steps"]
    with _workbench_jobs_lock:
        prev = _active_workbench_jobs.get(name)
        if prev is not None and prev.is_alive():
            logger.warning(
                "策略 %s 仍有工作台任务运行中，新任务启动前将尝试回收 DuckDB / worker",
                name,
            )
            _workbench_duckdb_prepare_for_run()
        thread = threading.Thread(
            target=_run_workbench_job_in_thread,
            args=(jid, name, norm_step, discovered, force_refresh),
            daemon=True,
            name=f"workbench-run-{jid[:8]}",
        )
        _active_workbench_jobs[name] = thread
        thread.start()
    return {
        "is_triggered": True,
        "job_id": jid,
        "run_id": jid,
        "steps": steps_payload,
    }
