"""Workbench async run for UI (V2-05 / V2-06 / V2-06b).

Runs ``Strategy.simulate`` in a daemon thread; progress via strategy
``PipelineProgress`` (core module owns weighting + disk).
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.infra.task_guard import TaskGuard
from core.infra.task_guard.contracts import TaskLeaseBusyError
from core.modules.strategy import Strategy
from core.modules.strategy.contracts import WorkbenchStep
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.progress import PipelineProgress

logger = logging.getLogger(__name__)


class WorkbenchRunLauncher:
    """UI async workbench run: lease / PipelineProgress / Strategy.simulate thread."""

    _LOCK = threading.Lock()
    _ACTIVE_BY_STRATEGY: Dict[str, str] = {}

    @staticmethod
    def normalize_step(step: str) -> Optional[str]:
        parsed = WorkbenchStep.try_parse(step)
        return parsed.value if parsed is not None else None

    @classmethod
    def submit(
        cls,
        *,
        strategy_name: str,
        step: str,
        api_settings: Dict[str, Any],
        force_refresh: bool,
    ) -> Dict[str, Any]:
        name = str(strategy_name or "").strip()
        norm = cls.normalize_step(step)
        if not name:
            return {"is_triggered": False, "reason": "strategy_name 无效"}
        if norm is None:
            return {"is_triggered": False, "reason": "step 须为 enum / price / portfolio"}
        if not isinstance(api_settings, dict):
            return {"is_triggered": False, "reason": "settings 必须为对象"}

        info = DiscoveryService.find_strategy(name)
        if info is None:
            discovered = cls._find_any(name)
            if discovered is None:
                return {"is_triggered": False, "reason": f"策略不存在: {name}"}
            if not discovered.is_enabled:
                return {"is_triggered": False, "reason": "策略未启用"}
            return {"is_triggered": False, "reason": f"策略不可运行: {name}"}

        status = TaskGuard.read_status()
        if status.get("busy"):
            kind = status.get("kind") or "unknown"
            return {
                "is_triggered": False,
                "reason": f"系统任务进行中（{kind}），请稍后再试",
            }

        with cls._LOCK:
            active = str(cls._ACTIVE_BY_STRATEGY.get(name) or "").strip()
            if active:
                return {
                    "is_triggered": False,
                    "reason": "该策略已有任务在运行中，请稍后重试",
                }
            jid = f"wb-run-{uuid.uuid4().hex[:12]}"
            cls._ACTIVE_BY_STRATEGY[name] = jid

        PipelineProgress.seed(
            name,
            jid,
            pipeline_name=norm,
            pipeline_description=PipelineProgress.pipeline_description(norm),
        )
        thread = threading.Thread(
            target=cls._background_job,
            args=(jid, name, norm, dict(api_settings), bool(force_refresh)),
            daemon=True,
            name=f"wb-run-{jid[:8]}",
        )
        thread.start()
        return {
            "is_triggered": True,
            "job_id": jid,
            "run_id": jid,
            "pipeline_id": jid,
            "pipeline_name": norm,
            "pipeline_description": PipelineProgress.pipeline_description(norm),
        }

    @classmethod
    def get_run_progress(
        cls,
        *,
        strategy_name: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        sn = str(strategy_name or "").strip()
        jid = str(job_id or "").strip()
        if not jid:
            return None
        doc = PipelineProgress.get(sn, jid, apply_stale=True)
        if not doc:
            return None
        # HTTP aliases for existing clients (run_id / phase).
        out = dict(doc)
        out.setdefault("run_id", out.get("pipeline_id") or jid)
        out.setdefault("job_id", out.get("pipeline_id") or jid)
        out.setdefault("phase", out.get("status"))
        return out

    @classmethod
    def get_step_progress(
        cls,
        *,
        strategy_name: str,
        normalized_step: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        """V2-06 legacy: path step must match pipeline_name."""
        env = cls.get_run_progress(strategy_name=strategy_name, job_id=job_id)
        if not env:
            return None
        step = str(normalized_step or "").strip()
        if str(env.get("pipeline_name") or "").strip() != step:
            return None
        jid = str(job_id or "").strip()
        status = str(env.get("status") or "").strip().lower()
        try:
            pct = float(env.get("progress") or 0.0)
        except (TypeError, ValueError):
            pct = 0.0
        out: Dict[str, Any] = {
            "progress": round(pct, 2),
            "status": status or "running",
            "job_id": jid,
        }
        result = env.get("result") if isinstance(env.get("result"), dict) else {}
        if status == "completed":
            out["is_success"] = True
            vid = result.get("version_id")
            if vid:
                out["version_id"] = str(vid)
        elif status in ("failed", "cancelled"):
            out["is_success"] = False
            if env.get("error"):
                out["reason"] = str(env.get("error"))
        return out

    @classmethod
    def _find_any(cls, key_or_id: str):
        needle = str(key_or_id or "").strip()
        if not needle:
            return None
        for info in DiscoveryService.discover_strategies():
            if info.id() == needle or info.key == needle:
                return info
        return None

    @classmethod
    def _background_job(
        cls,
        job_id: str,
        strategy_name: str,
        norm_step: str,
        api_settings: Dict[str, Any],
        force_refresh: bool,
    ) -> None:
        lease = TaskGuard.lease(
            kind="strategy_run",
            job_id=job_id,
            resource_key=strategy_name,
            label=f"strategy_run:{strategy_name}:{norm_step}",
            domains=["data", "strategy"],
        )
        try:
            lease.acquire()
        except TaskLeaseBusyError as exc:
            inst = PipelineProgress.load(strategy_name, job_id)
            if inst is not None:
                inst.fail(str(exc))
            cls._clear_active(strategy_name, job_id)
            return

        try:
            with PipelineProgress.bind(strategy_name, job_id) as prog:
                prog.mark_running()
                cls._duckdb_prepare()
                kind = WorkbenchStep.parse(norm_step).to_simulate_kind()
                result = Strategy.simulate(
                    strategy_name,
                    kind=kind,
                    ignore_cache=force_refresh,
                    runtime_settings=api_settings,
                )
                wb_version = int((result or {}).get("_workbench_version") or 0)
                payload: Dict[str, Any] = {"message": f"{norm_step} 已完成"}
                if wb_version > 0:
                    payload["version_id"] = f"v{wb_version}"
                    payload["report_step"] = norm_step
                prog.complete(result=payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Workbench run failed job_id=%s", job_id)
            inst = PipelineProgress.load(strategy_name, job_id)
            if inst is not None:
                inst.fail(str(exc))
            else:
                try:
                    with PipelineProgress.bind(strategy_name, job_id) as prog:
                        prog.fail(str(exc))
                except Exception:
                    logger.exception("PipelineProgress.fail unavailable job_id=%s", job_id)
        finally:
            cls._duckdb_finalize()
            try:
                lease.release()
            except Exception:
                logger.exception("pipeline lease release failed")
            cls._clear_active(strategy_name, job_id)

    @classmethod
    def _clear_active(cls, strategy_name: str, job_id: str) -> None:
        with cls._LOCK:
            if cls._ACTIVE_BY_STRATEGY.get(strategy_name) == job_id:
                cls._ACTIVE_BY_STRATEGY.pop(strategy_name, None)

    @staticmethod
    def _duckdb_prepare() -> None:
        try:
            from core.infra.db import Db

            wp = Db.duckdb.worker_pool
            if wp.is_backend():
                wp.recover_after_interrupt()
        except Exception as exc:
            logger.warning("Workbench DuckDB prepare: %s", exc)

    @staticmethod
    def _duckdb_finalize() -> None:
        try:
            from core.infra.db import Db

            wp = Db.duckdb.worker_pool
            if not wp.is_backend():
                return
            wp.wait_pool_children_done(timeout_sec=30.0)
            from core.modules.data_manager import DataManager

            DataManager.ensure_restored_after_worker_pool()
        except Exception as exc:
            logger.warning("Workbench DuckDB finalize: %s", exc)


__all__ = ["WorkbenchRunLauncher"]
