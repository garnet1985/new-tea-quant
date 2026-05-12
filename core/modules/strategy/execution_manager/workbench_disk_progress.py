"""工作台步骤：进度 JSON 落盘与 GET progress 组装（唯一数据源为 ``ProgressRecorder``）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.services.progress import ProgressRecorder


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
        from core.modules.strategy.launcher.workbench import (
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
        raw_enum = rr.get("enum")
        if isinstance(raw_enum, dict) and raw_enum:
            out["enum"] = raw_enum
        else:
            e = _enum_summary_from_result_report(rr)
            if e:
                out["enum"] = e

    elif normalized_step == "price":
        e = _enum_summary_from_result_report(rr)
        if e:
            out["enum"] = e
        p = _price_factor_summary_from_result_report(rr)
        if p:
            out["price"] = p
        raw_pf = rr.get("price_factor")
        if isinstance(raw_pf, dict) and raw_pf:
            out["price_factor"] = raw_pf

    elif normalized_step == "capital":
        e = _enum_summary_from_result_report(rr)
        if e:
            out["enum"] = e
        p = _price_factor_summary_from_result_report(rr)
        if p:
            out["price"] = p
        raw_pf = rr.get("price_factor")
        if isinstance(raw_pf, dict) and raw_pf:
            out["price_factor"] = raw_pf
        raw = rr.get("capital_allocation")
        if isinstance(raw, dict) and raw:
            out["capital_allocation"] = raw

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


def merge_snapshot_into_disk_progress(
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
    """运行中段更新进度文件中的 ``progress_pct``（不写 ``snapshot_id``；完成仍由 merge 写 100）。"""
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
            "progress_pct": 5,
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


__all__ = [
    "disk_mark_failed",
    "disk_mark_running",
    "disk_workbench_step_progress",
    "get_step_progress",
    "merge_snapshot_into_disk_progress",
    "seed_workbench_progress_file",
]
