"""工作台单步运行：进程内 ``_JOBS``（后台任务状态）、触发 run（V2-05）；``GET progress`` 读进度文件（V2-06）。

进度 JSON 的清理不在此处触发，由后续 infra / 运维入口统一处理。

模块顶层避免导入 ``price_factor`` / ``capital_allocation`` / ``enumerator``，以免经 DbCache
链式导入 ``cache_service`` → BFF（Flask）。
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional, Tuple

from core.infra.project_context.path_manager import PathManager
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import DiscoveredStrategy
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper
from core.modules.strategy.services.launcher.run_service import StrategySettingsService
from core.modules.strategy.services.progress import ProgressRecorder

logger = logging.getLogger(__name__)

_VALID_STEPS = frozenset({"enum", "price", "capital"})

# --- 进程内 job 表 ---

_LOCK = threading.Lock()
_JOBS: Dict[str, Dict[str, Any]] = {}


def job_create(*, strategy_name: str, step: str, is_force: bool) -> str:
    jid = str(uuid.uuid4())
    name = str(strategy_name).strip()
    st = str(step).strip()
    with _LOCK:
        _JOBS[jid] = {
            "strategy_name": name,
            "step": st,
            "is_force": bool(is_force),
            "progress": 0.0,
            "status": "queued",
            "error": None,
            "snapshot_id": 0,
        }
    return jid


def job_update(job_id: str, **fields: Any) -> None:
    with _LOCK:
        row = _JOBS.get(job_id)
        if row is None:
            return
        row.update(fields)


def _enum_summary_from_result_report(rr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = rr.get("enum")
    if not isinstance(raw, dict) or not raw:
        return None
    merged = dict(raw)
    try:
        merged["opportunities"] = int(merged.get("opportunities", 0) or 0)
    except (TypeError, ValueError):
        merged["opportunities"] = 0
    return merged


def _price_factor_summary_from_result_report(rr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = rr.get("price_factor")
    if not isinstance(raw, dict) or not raw:
        return None
    merged = dict(raw)
    try:
        wr = float(merged.get("win_rate", merged.get("winRate", 0)) or 0)
    except (TypeError, ValueError):
        wr = 0.0
    merged["winRate"] = round(wr, 2)
    try:
        ar = float(merged.get("avg_roi", merged.get("roi", merged.get("avgRoi", 0))) or 0)
    except (TypeError, ValueError):
        ar = 0.0
    if ar != 0.0 and abs(ar) < 1.0:
        merged["roi"] = round(ar * 100.0, 2)
    else:
        merged["roi"] = round(ar, 2)
    return merged


def _fed_result_report_slice(
    strategy_name: str,
    normalized_step: str,
    snapshot_id: int,
) -> Dict[str, Any]:
    """从工作台快照 ``result_report`` 取出当前 step  execution 条需要的摘要（与 FED 执行面板字段对齐）。"""
    if snapshot_id <= 0:
        return {}
    try:
        from core.modules.strategy.services.launcher.workbench import (
            fetch_workbench_snapshot_by_snapshot_id,
        )
    except Exception:
        return {}

    row = fetch_workbench_snapshot_by_snapshot_id(
        str(strategy_name).strip(),
        int(snapshot_id),
    )
    if not row:
        return {}
    rr = row.get("result_report") or {}
    out: Dict[str, Any] = {}

    if normalized_step == "enum":
        e = _enum_summary_from_result_report(rr)
        if e:
            out["enum"] = e

    elif normalized_step == "price":
        # 单独跑价格步时，快照里仍带有本轮依赖的枚举摘要，一并下发供执行面板 / 报告用
        e = _enum_summary_from_result_report(rr)
        if e:
            out["enum"] = e
        p = _price_factor_summary_from_result_report(rr)
        if p:
            out["price"] = p

    elif normalized_step == "capital":
        e = _enum_summary_from_result_report(rr)
        if e:
            out["enum"] = e
        p = _price_factor_summary_from_result_report(rr)
        if p:
            out["price"] = p
        raw = rr.get("capital_allocation")
        if isinstance(raw, dict) and raw:

            def _num(val: Any, default: float = 0.0) -> float:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            profit = _num(raw.get("profit", raw.get("total_profit")))
            ic = _num(raw.get("initialCapital", raw.get("initial_capital")))
            ec = _num(raw.get("endCapital", raw.get("end_capital")))
            if ec == 0.0 and (ic != 0.0 or profit != 0.0):
                ec = ic + profit
            ret_pct = _num(raw.get("retPct", raw.get("return_pct", raw.get("ret_pct"))))
            out["capital"] = {
                "profit": profit,
                "retPct": round(ret_pct, 4),
                "initialCapital": ic,
                "endCapital": ec,
            }

    return out


def _merge_snapshot_into_disk_progress(
    strategy_name: str,
    job_id: str,
    normalized_step: str,
    snapshot_id: int,
) -> None:
    """完成后把 ``snapshot_id`` 写入进度 JSON（轮询只读该文件）。"""
    sid = int(snapshot_id or 0)
    if sid <= 0:
        return
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    step = str(normalized_step).strip()
    rec = ProgressRecorder.for_strategy_run_step(sn, jid, step)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    base.update(
        {
            "strategy_name": sn,
            "run_id": jid,
            "step_name": step,
            "progress_pct": 100,
            "snapshot_id": sid,
            "status": "completed",
            "phase": "completed",
        }
    )
    base.pop("error", None)
    rec.record(base)


def _seed_workbench_progress_file(
    strategy_name: str,
    job_id: str,
    normalized_step: str,
) -> None:
    """POST 返回 ``job_id`` 后立即落盘，轮询只读该文件，不依赖进程内 ``_JOBS``。"""
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    step = str(normalized_step).strip()
    ProgressRecorder.for_strategy_run_step(sn, jid, step).record(
        {
            "strategy_name": sn,
            "run_id": jid,
            "step_name": step,
            "phase": "queued",
            "progress_pct": 0,
        }
    )


def _disk_mark_running(strategy_name: str, job_id: str, normalized_step: str) -> None:
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    step = str(normalized_step).strip()
    rec = ProgressRecorder.for_strategy_run_step(sn, jid, step)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    base.update(
        {
            "strategy_name": sn,
            "run_id": jid,
            "step_name": step,
            "phase": "running",
            "progress_pct": 5,
        }
    )
    rec.record(base)


def _disk_mark_failed(
    strategy_name: str,
    job_id: str,
    normalized_step: str,
    error: str,
) -> None:
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    step = str(normalized_step).strip()
    rec = ProgressRecorder.for_strategy_run_step(sn, jid, step)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    base.update(
        {
            "strategy_name": sn,
            "run_id": jid,
            "step_name": step,
            "phase": "failed",
            "status": "failed",
            "progress_pct": 100,
            "error": str(error),
        }
    )
    rec.record(base)


def _progress_payload_from_disk(
    strategy_name: str,
    normalized_step: str,
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """``GET progress`` 唯一数据源：``userspace_tmp/progress/strategy-workbench/*.json``。"""
    jid = str(job_id or "").strip()
    if not jid:
        return None
    name = str(strategy_name).strip()
    step = str(normalized_step).strip()
    disk = ProgressRecorder.for_strategy_run_step(name, jid, step).get_progress()
    if not isinstance(disk, dict) or not disk:
        return None
    sn = str(disk.get("strategy_name") or "").strip()
    if sn and sn != name:
        return None
    st = str(disk.get("step_name") or "").strip()
    if st and st != step:
        return None

    disk_status = str(disk.get("status") or "").strip().lower()
    phase = str(disk.get("phase") or "").strip().lower()
    if disk_status == "failed" or phase == "failed":
        err = disk.get("error")
        out: Dict[str, Any] = {
            "progress": 100.0,
            "status": "failed",
            "job_id": jid,
            "is_success": False,
        }
        if err:
            out["reason"] = str(err)
        return out

    try:
        pct = float(disk.get("progress_pct") or 0)
    except (TypeError, ValueError):
        pct = 0.0
    sid_disk = int(disk.get("snapshot_id") or 0)
    if sid_disk > 0 and pct < 100.0:
        pct = 100.0
    pct = max(0.0, min(100.0, pct))
    done = pct >= 100.0 or sid_disk > 0
    status = "completed" if done else "running"
    out = {
        "progress": round(pct, 2),
        "status": status,
        "job_id": jid,
    }
    if done:
        out["is_success"] = True
        sid = sid_disk
        if sid > 0:
            out["snapshot_id"] = sid
            out["version_id"] = f"v{sid}"
            fed = _fed_result_report_slice(name, step, sid)
            if fed:
                out["result_report"] = fed
    else:
        out["is_success"] = None
    return out


def get_step_progress(
    *,
    strategy_name: str,
    normalized_step: str,
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """V2-06：进度仅来自进度文件（见 ``_progress_payload_from_disk``）。"""
    jid_in = str(job_id or "").strip()
    if not jid_in:
        return None
    return _progress_payload_from_disk(strategy_name, normalized_step, jid_in)




# --- V2-05：后台线程执行 flow，HTTP 立即返回 job_id 供轮询 ---
#
# 枚举耗时较长时，若在请求线程内同步执行，浏览器会一直阻塞在 POST 上无法渲染进度。
# 另启线程运行步骤；ProcessWorker 在非主线程初始化时需跳过 ``signal.signal``（见
# ``process_worker._setup_signal_handlers``）。


def normalize_step(step: str) -> Optional[str]:
    s = str(step or "").strip().lower()
    return s if s in _VALID_STEPS else None


def _resolve_discovered(
    strategy_name: str, api_settings: Dict[str, Any]
) -> Tuple[Optional[DiscoveredStrategy], Optional[str]]:
    folder = PathManager.userspace() / "strategies" / strategy_name
    base = StrategyDiscoveryHelper.load_strategy(folder)
    if base is None:
        return None, "策略不存在或无法加载"

    normalized, err = StrategySettingsService.normalize_runtime_settings(
        strategy_name=strategy_name,
        api_settings=api_settings,
    )
    if err or not normalized:
        return None, err or "settings 校验失败"

    st = StrategySettings(raw_settings=dict(normalized))
    vr = st.validate()
    if not vr.is_usable():
        return None, "settings 校验失败"

    discovered = DiscoveredStrategy(
        name=base.name,
        folder=base.folder,
        worker_class=base.worker_class,
        worker_module_path=base.worker_module_path,
        worker_class_name=base.worker_class_name,
        settings=st,
    )
    discovered.validate_required_fields()
    return discovered, None


def _run_step_and_snapshot_id(
    step: str,
    strategy_name: str,
    discovered: DiscoveredStrategy,
    *,
    is_force: bool,
    job_id: str,
) -> int:
    if step == "enum":
        from core.modules.strategy.services.launcher.enumerator_runtime_service import (
            EnumeratorRuntimeService,
        )

        ctx = EnumeratorRuntimeService.build_context(
            strategy_name=strategy_name,
            strategy_info=discovered,
            raw_settings_override=discovered.settings.to_dict(),
            force_refresh=is_force,
            workbench_run_id=job_id,
            workbench_strategy_name=strategy_name,
        )
        EnumeratorRuntimeService.run_enum(ctx)
        return int(ctx.flow.last_snapshot_id or 0)

    if step == "price":
        from core.modules.strategy.engines.simulator.price_factor.price_factor_flow import PriceFactorFlow

        flow = PriceFactorFlow(is_verbose=False, force_refresh=is_force)
        flow.run(strategy_name, discovered)
        return int(flow.last_snapshot_id or 0)

    if step == "capital":
        from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow import (
            CapitalAllocationFlow,
        )

        flow = CapitalAllocationFlow(is_verbose=False, force_refresh=is_force)
        flow.run(strategy_name, discovered)
        return int(flow.last_snapshot_id or 0)

    raise ValueError(f"未知 step: {step!r}")


def _background_job(
    job_id: str,
    strategy_name: str,
    step: str,
    discovered: DiscoveredStrategy,
    is_force: bool,
) -> None:
    job_update(job_id, status="running", progress=1.0)
    _disk_mark_running(strategy_name, job_id, step)
    try:
        job_update(job_id, progress=5.0)
        sid = _run_step_and_snapshot_id(
            step,
            strategy_name,
            discovered,
            is_force=is_force,
            job_id=job_id,
        )
        sid_int = int(sid or 0)
        job_update(
            job_id,
            status="completed",
            progress=100.0,
            snapshot_id=sid_int,
        )
        _merge_snapshot_into_disk_progress(strategy_name, job_id, step, sid_int)
    except Exception as exc:  # noqa: BLE001 — 任务边界兜底
        logger.exception("Workbench step run failed job_id=%s", job_id)
        job_update(job_id, status="failed", progress=100.0, error=str(exc))
        _disk_mark_failed(strategy_name, job_id, step, str(exc))


def trigger_workbench_step_run(
    *,
    strategy_name: str,
    step: str,
    api_settings: Dict[str, Any],
    is_force: bool,
) -> Dict[str, Any]:
    norm_step = normalize_step(step)
    if norm_step is None:
        return {"is_triggered": False, "reason": f"step 须为 enum / price / capital，收到 {step!r}"}

    name = str(strategy_name or "").strip()
    if not name:
        return {"is_triggered": False, "reason": "strategy_name 无效"}

    discovered, err = _resolve_discovered(name, api_settings)
    if err or discovered is None:
        return {"is_triggered": False, "reason": err or "无法解析策略"}

    jid = job_create(strategy_name=name, step=norm_step, is_force=is_force)
    _seed_workbench_progress_file(name, jid, norm_step)
    thread = threading.Thread(
        target=_background_job,
        args=(jid, name, norm_step, discovered, is_force),
        daemon=True,
        name=f"workbench-run-{jid[:8]}",
    )
    thread.start()
    return {"is_triggered": True, "job_id": jid}
