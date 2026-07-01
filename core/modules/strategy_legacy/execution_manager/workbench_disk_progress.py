"""工作台步骤：进度 JSON 落盘与 GET progress 组装（唯一数据源为 ``ProgressRecorder``）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.services.progress import ProgressRecorder


def merge_version_into_disk_progress(
    strategy_name: str,
    job_id: str,
    normalized_step: str,
    version: int,
) -> None:
    """完成后把工作台 ``version`` 写入进度 JSON（轮询只读该文件）。"""
    sid = int(version or 0)
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
            "version": sid,
            "status": "completed",
            "phase": "completed",
        }
    )
    base.pop("error", None)
    rec.record(base)


def seed_workbench_progress_file(
    strategy_name: str,
    job_id: str,
    normalized_step: str,
) -> None:
    """POST 返回 ``job_id`` 后立即落盘，轮询只读该文件，不依赖进程内 job 表。"""
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


def disk_workbench_step_progress(
    strategy_name: str,
    job_id: str,
    normalized_step: str,
    progress_pct: float,
    *,
    phase: str = "running",
) -> None:
    """运行中段更新进度文件中的 ``progress_pct``（不写 ``version``；完成仍由 merge 写 100）。"""
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    step = str(normalized_step).strip()
    rec = ProgressRecorder.for_strategy_run_step(sn, jid, step)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    try:
        pct = float(progress_pct)
    except (TypeError, ValueError):
        pct = 0.0
    pct = max(0.0, min(99.9, pct))
    base.update(
        {
            "strategy_name": sn,
            "run_id": jid,
            "step_name": step,
            "phase": phase,
            "status": "running",
            "progress_pct": round(pct, 2),
        }
    )
    rec.record(base)


def disk_mark_running(strategy_name: str, job_id: str, normalized_step: str) -> None:
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
            "progress_pct": 1,
        }
    )
    rec.record(base)


def disk_mark_failed(
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
    sid_disk = int(disk.get("version") or 0)
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
            out["version"] = sid
            out["version_id"] = f"v{sid}"
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


__all__ = [
    "disk_mark_failed",
    "disk_mark_running",
    "disk_workbench_step_progress",
    "get_step_progress",
    "merge_version_into_disk_progress",
    "seed_workbench_progress_file",
]
