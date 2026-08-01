"""Workbench run envelope on disk (V2-05 / V2-06b)."""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.services.progress import ProgressRecorder

from .workbench_step_progress import WorkbenchStepProgress

logger = logging.getLogger(__name__)


class WorkbenchRunEnvelope:
    """Persist / update / read the workbench run progress envelope."""

    SCHEMA = "workbench_run_v1"

    @staticmethod
    def _recorder(strategy_name: str, job_id: str) -> ProgressRecorder:
        return ProgressRecorder.for_strategy_workbench_run(strategy_name, job_id)

    @classmethod
    def _load(cls, strategy_name: str, job_id: str) -> Optional[Dict[str, Any]]:
        raw = cls._recorder(strategy_name, job_id).get_progress()
        if not isinstance(raw, dict):
            return None
        if raw.get("schema") != cls.SCHEMA:
            return None
        return raw

    @classmethod
    def _save(cls, strategy_name: str, job_id: str, env: Dict[str, Any]) -> None:
        cls._recorder(strategy_name, job_id).record(env)

    @classmethod
    def seed(
        cls,
        strategy_name: str,
        run_id: str,
        plan_steps: List[str],
    ) -> List[Dict[str, Any]]:
        sn = str(strategy_name).strip()
        jid = str(run_id).strip()
        names = [str(sub).strip() for sub in plan_steps if str(sub).strip()]
        steps: List[Dict[str, Any]] = [
            {
                "step_name": nm,
                "progress": 0.0,
                "status": "pending",
                "stage": None,
                "stage_label": None,
                "counters": None,
                "result": None,
            }
            for nm in names
        ]
        env: Dict[str, Any] = {
            "schema": cls.SCHEMA,
            "run_id": jid,
            "strategy_name": sn,
            "phase": "queued",
            "steps": steps,
        }
        cls._save(sn, jid, env)
        return copy.deepcopy(steps)

    @classmethod
    def mark_started(cls, strategy_name: str, run_id: str) -> None:
        env = cls._load(str(strategy_name).strip(), str(run_id).strip())
        if not env:
            return
        steps = env.get("steps") or []
        env["phase"] = "running"
        if steps:
            steps[0]["status"] = "running"
            steps[0]["progress"] = max(float(steps[0].get("progress") or 0), 1.0)
            steps[0]["stage"] = "load"
            steps[0]["stage_label"] = WorkbenchStepProgress.stage_label("load")
        env["steps"] = steps
        names = [str(s.get("step_name") or "").strip() for s in steps]
        env["run_progress"] = WorkbenchStepProgress.compute_run_progress(names, steps)
        cls._save(str(strategy_name).strip(), str(run_id).strip(), env)

    @classmethod
    def on_substep_start(
        cls,
        strategy_name: str,
        run_id: str,
        index: int,
        total: int,
        substep: str,
    ) -> None:
        _ = total
        sn = str(strategy_name).strip()
        jid = str(run_id).strip()
        env = cls._load(sn, jid)
        if not env:
            return
        steps = env.get("steps") or []
        for j, st in enumerate(steps):
            if j == index:
                st["status"] = "running"
                st["progress"] = max(float(st.get("progress") or 0), 1.0)
                st["stage"] = "execute"
                st["stage_label"] = WorkbenchStepProgress.stage_label("execute")
            elif j > index and st.get("status") not in ("completed", "failed"):
                st["status"] = "pending"
                st["progress"] = 0.0
                st["result"] = None
        env["phase"] = "running"
        env["steps"] = steps
        names = [str(s.get("step_name") or "").strip() for s in steps]
        env["run_progress"] = WorkbenchStepProgress.compute_run_progress(names, steps)
        cls._save(sn, jid, env)

    @classmethod
    def apply_step_stage(
        cls,
        strategy_name: str,
        run_id: str,
        substep: str,
        stage: str,
        stage_ratio: float = 0.0,
        *,
        counters: Optional[Dict[str, Any]] = None,
    ) -> None:
        sn = str(strategy_name).strip()
        jid = str(run_id).strip()
        env = cls._load(sn, jid)
        if not env:
            return
        steps = env.get("steps") or []
        sub = str(substep).strip()
        stg = str(stage).strip()
        prog = WorkbenchStepProgress.compute_step_progress_pct(sub, stg, stage_ratio)
        for st in steps:
            if st.get("step_name") != sub:
                continue
            if st.get("status") not in ("running", "pending"):
                break
            if st.get("status") == "pending":
                st["status"] = "running"
            st["stage"] = stg
            st["stage_label"] = WorkbenchStepProgress.stage_label(stg)
            try:
                cur = float(st.get("progress") or 0)
            except (TypeError, ValueError):
                cur = 0.0
            st["progress"] = round(max(cur, prog), 2)
            if counters is not None:
                st["counters"] = dict(counters)
            break
        names = [str(s.get("step_name") or "").strip() for s in steps]
        env["run_progress"] = WorkbenchStepProgress.compute_run_progress(names, steps)
        env["steps"] = steps
        cls._save(sn, jid, env)

    @classmethod
    def on_substep_finish(
        cls,
        strategy_name: str,
        run_id: str,
        index: int,
        total: int,
        substep: str,
        version: int,
    ) -> None:
        _ = total
        sn = str(strategy_name).strip()
        jid = str(run_id).strip()
        env = cls._load(sn, jid)
        if not env:
            return
        steps = env.get("steps") or []
        if index < 0 or index >= len(steps):
            return
        st = steps[index]
        sid = int(version or 0)
        st["status"] = "completed"
        st["progress"] = 100.0
        st["stage"] = "report"
        st["stage_label"] = WorkbenchStepProgress.stage_label("report")
        st.pop("counters", None)
        msg = f"{str(substep).strip()} 已完成"
        if sid > 0:
            st["result"] = {
                "message": msg,
                "version_id": f"v{sid}",
                "report_step": str(substep).strip(),
            }
        else:
            st["result"] = {"message": msg}
        names = [str(s.get("step_name") or "").strip() for s in steps]
        env["run_progress"] = WorkbenchStepProgress.compute_run_progress(names, steps)
        env["steps"] = steps
        cls._save(sn, jid, env)

    @classmethod
    def mark_phase_completed(cls, strategy_name: str, run_id: str) -> None:
        sn = str(strategy_name).strip()
        jid = str(run_id).strip()
        env = cls._load(sn, jid)
        if not env:
            return
        env["phase"] = "completed"
        steps = env.get("steps") or []
        names = [str(s.get("step_name") or "").strip() for s in steps]
        env["run_progress"] = WorkbenchStepProgress.compute_run_progress(names, steps)
        if isinstance(env.get("run_progress"), dict):
            env["run_progress"]["pct"] = 100.0
        cls._save(sn, jid, env)

    @classmethod
    def fail(
        cls,
        strategy_name: str,
        run_id: str,
        step_index: int,
        message: str,
    ) -> None:
        sn = str(strategy_name).strip()
        jid = str(run_id).strip()
        env = cls._load(sn, jid)
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
        cls._save(sn, jid, env)

    @classmethod
    def get_run_progress(
        cls,
        *,
        strategy_name: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        sn = str(strategy_name).strip()
        jid = str(job_id).strip()
        if not jid:
            return None
        env = cls._load(sn, jid)
        if not env:
            return None
        steps = copy.deepcopy(env.get("steps") or [])
        names = [str(s.get("step_name") or "").strip() for s in steps]
        run_progress = WorkbenchStepProgress.compute_run_progress(names, steps)
        return {
            "run_id": jid,
            "phase": str(env.get("phase") or "queued"),
            "run_progress": run_progress,
            "steps": steps,
        }

    @classmethod
    def get_step_progress(
        cls,
        *,
        strategy_name: str,
        normalized_step: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        """V2-06 legacy single-step view derived from run envelope."""
        env = cls.get_run_progress(strategy_name=strategy_name, job_id=job_id)
        if not env:
            return None
        step = str(normalized_step or "").strip()
        jid = str(job_id or "").strip()
        for row in env.get("steps") or []:
            if str(row.get("step_name") or "").strip() != step:
                continue
            status = str(row.get("status") or "").strip().lower()
            try:
                pct = float(row.get("progress") or 0.0)
            except (TypeError, ValueError):
                pct = 0.0
            out: Dict[str, Any] = {
                "progress": round(pct, 2),
                "status": status or "running",
                "job_id": jid,
            }
            result = row.get("result") if isinstance(row.get("result"), dict) else {}
            if status == "completed":
                out["is_success"] = True
                vid = result.get("version_id")
                if vid:
                    out["version_id"] = str(vid)
            elif status == "failed":
                out["is_success"] = False
                if result.get("message"):
                    out["reason"] = str(result.get("message"))
            return out
        return None


__all__ = ["WorkbenchRunEnvelope"]
