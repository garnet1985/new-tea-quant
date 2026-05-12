"""工作台单次 run 的编排信封：落盘 ``steps[]``，供 ``GET …/run/progress`` 聚合读取。"""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.services.progress import ProgressRecorder

from .workbench_disk_progress import _fed_execution_step_card_slice

logger = logging.getLogger(__name__)

RUN_ENVELOPE_SCHEMA = "workbench_run_v1"

def _rec(sn: str, jid: str) -> ProgressRecorder:
    return ProgressRecorder.for_strategy_workbench_run(sn, jid)


def _load_env(sn: str, jid: str) -> Optional[Dict[str, Any]]:
    raw = _rec(sn, jid).get_progress()
    if not isinstance(raw, dict):
        return None
    if raw.get("schema") != RUN_ENVELOPE_SCHEMA:
        return None
    return raw


def _save_env(sn: str, jid: str, env: Dict[str, Any]) -> None:
    _rec(sn, jid).record(env)


def seed_workbench_run_envelope(
    strategy_name: str,
    run_id: str,
    plan: List[Tuple[str, bool]],
) -> List[Dict[str, Any]]:
    """写入 queued 信封；返回 ``steps`` 列表供 POST 响应。"""
    sn = str(strategy_name).strip()
    jid = str(run_id).strip()
    names = [str(sub).strip() for sub, _ in plan if str(sub).strip()]
    steps: List[Dict[str, Any]] = [
        {
            "step_name": nm,
            "progress": 0.0,
            "status": "pending",
            "result": None,
        }
        for nm in names
    ]
    env: Dict[str, Any] = {
        "schema": RUN_ENVELOPE_SCHEMA,
        "run_id": jid,
        "strategy_name": sn,
        "phase": "queued",
        "steps": steps,
    }
    _save_env(sn, jid, env)
    return copy.deepcopy(steps)


def run_envelope_mark_started(strategy_name: str, run_id: str) -> None:
    env = _load_env(str(strategy_name).strip(), str(run_id).strip())
    if not env:
        return
    steps = env.get("steps") or []
    env["phase"] = "running"
    if steps:
        steps[0]["status"] = "running"
        steps[0]["progress"] = max(float(steps[0].get("progress") or 0), 1.0)
    env["steps"] = steps
    _save_env(str(strategy_name).strip(), str(run_id).strip(), env)


def run_envelope_on_substep_start(
    strategy_name: str,
    run_id: str,
    index: int,
    total: int,
    substep: str,
) -> None:
    _ = total, substep
    sn = str(strategy_name).strip()
    jid = str(run_id).strip()
    env = _load_env(sn, jid)
    if not env:
        return
    steps = env.get("steps") or []
    for j, st in enumerate(steps):
        if j == index:
            st["status"] = "running"
            cur = float(st.get("progress") or 0)
            st["progress"] = max(cur, 1.0)
        elif j > index and st.get("status") not in ("completed", "failed"):
            st["status"] = "pending"
            st["progress"] = 0.0
            st["result"] = None
    env["phase"] = "running"
    env["steps"] = steps
    _save_env(sn, jid, env)


def run_envelope_on_overall_pct(strategy_name: str, run_id: str, pct: float) -> None:
    sn = str(strategy_name).strip()
    jid = str(run_id).strip()
    env = _load_env(sn, jid)
    if not env:
        return
    steps = env.get("steps") or []
    try:
        v = float(pct)
    except (TypeError, ValueError):
        v = 0.0
    v = max(0.0, min(99.9, v))
    for st in steps:
        if st.get("status") == "running":
            st["progress"] = round(v, 2)
            break
    env["steps"] = steps
    _save_env(sn, jid, env)


def run_envelope_on_flow_progress(
    strategy_name: str,
    run_id: str,
    substep: str,
    flow_pct: float,
) -> None:
    sn = str(strategy_name).strip()
    jid = str(run_id).strip()
    env = _load_env(sn, jid)
    if not env:
        return
    steps = env.get("steps") or []
    try:
        fp = float(flow_pct)
    except (TypeError, ValueError):
        fp = 0.0
    fp = max(0.0, min(100.0, fp))
    sub = str(substep).strip()
    for st in steps:
        if st.get("step_name") == sub and st.get("status") == "running":
            st["progress"] = round(fp, 2)
            break
    env["steps"] = steps
    _save_env(sn, jid, env)


def run_envelope_on_substep_finish(
    strategy_name: str,
    run_id: str,
    index: int,
    total: int,
    substep: str,
    snapshot_id: int,
) -> None:
    _ = total
    sn = str(strategy_name).strip()
    jid = str(run_id).strip()
    env = _load_env(sn, jid)
    if not env:
        return
    steps = env.get("steps") or []
    if index < 0 or index >= len(steps):
        return
    st = steps[index]
    if str(st.get("step_name") or "") != str(substep).strip():
        logger.warning(
            "run envelope step mismatch at index %s: expected %r got %r",
            index,
            st.get("step_name"),
            substep,
        )
    sid = int(snapshot_id or 0)
    st["status"] = "completed"
    st["progress"] = 100.0
    msg = f"{str(substep).strip()} 已完成"
    if sid > 0:
        # ``card``：仅执行面板三行所需标量，避免塞整份 ``result_report``；完整报告见 ``GET …/report``。
        card = _fed_execution_step_card_slice(sn, str(substep).strip(), sid)
        st["result"] = {
            "message": msg,
            "version_id": f"v{sid}",
            "report_step": str(substep).strip(),
            "card": card if card else None,
        }
    else:
        st["result"] = {"message": msg}
    env["steps"] = steps
    _save_env(sn, jid, env)


def run_envelope_mark_phase_completed(strategy_name: str, run_id: str) -> None:
    sn = str(strategy_name).strip()
    jid = str(run_id).strip()
    env = _load_env(sn, jid)
    if not env:
        return
    env["phase"] = "completed"
    _save_env(sn, jid, env)


def run_envelope_fail(
    strategy_name: str,
    run_id: str,
    step_index: int,
    message: str,
) -> None:
    sn = str(strategy_name).strip()
    jid = str(run_id).strip()
    env = _load_env(sn, jid)
    if not env:
        return
    steps = env.get("steps") or []
    msg = str(message or "").strip() or "执行失败"
    if steps and 0 <= step_index < len(steps):
        st = steps[step_index]
        if st.get("status") != "completed":
            st["status"] = "failed"
            st["progress"] = 100.0
            st["result"] = {"message": msg}
    env["phase"] = "failed"
    env["steps"] = steps
    _save_env(sn, jid, env)


def get_run_progress(
    *,
    strategy_name: str,
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """供 BFF ``GET …/run/progress``：合并枚举细粒度进度侧车。"""
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    if not jid:
        return None
    env = _load_env(sn, jid)
    if not env:
        return None
    steps = copy.deepcopy(env.get("steps") or [])
    for st in steps:
        if st.get("step_name") == "enum" and st.get("status") == "running":
            side = ProgressRecorder.for_strategy_run_step(sn, jid, "enum").get_progress()
            if isinstance(side, dict):
                try:
                    ep = float(side.get("progress_pct") or 0)
                except (TypeError, ValueError):
                    ep = 0.0
                ep = max(0.0, min(100.0, ep))
                try:
                    cur = float(st.get("progress") or 0)
                except (TypeError, ValueError):
                    cur = 0.0
                st["progress"] = round(max(cur, ep), 2)
            break
    return {
        "run_id": jid,
        "phase": str(env.get("phase") or "queued"),
        "steps": steps,
    }


__all__ = [
    "RUN_ENVELOPE_SCHEMA",
    "get_run_progress",
    "run_envelope_fail",
    "run_envelope_mark_phase_completed",
    "run_envelope_mark_started",
    "run_envelope_on_flow_progress",
    "run_envelope_on_overall_pct",
    "run_envelope_on_substep_finish",
    "run_envelope_on_substep_start",
    "seed_workbench_run_envelope",
]
