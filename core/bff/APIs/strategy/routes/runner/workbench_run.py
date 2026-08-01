"""Workbench async run for UI (V2-05 / V2-06 / V2-06b).

Runs ``Strategy.simulate`` in a daemon thread; progress via run envelope files.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, List, Optional

from core.infra.system_actions.cache_cleanup.pipeline_lease import (
    PipelineLease,
    PipelineLeaseBusyError,
    read_pipeline_status,
)
from core.modules.strategy import Strategy
from core.modules.strategy.core.enums import SimulateKind, WorkbenchStep
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.services.simulation_cache.cache_manager import (
    SimulationCacheManager,
)
from core.modules.strategy.core.services.simulation_cache.fingerprints import (
    FingerprintCalculator,
)

from .workbench_run_envelope import WorkbenchRunEnvelope

logger = logging.getLogger(__name__)


class WorkbenchRunLauncher:
    """UI async workbench run: lease / envelope / Strategy.simulate thread."""

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

        pipeline = read_pipeline_status()
        if pipeline.get("busy"):
            kind = pipeline.get("kind") or "unknown"
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

        plan_steps = cls._plan_ui_steps(
            name,
            norm,
            force_refresh=bool(force_refresh),
            runtime_settings=api_settings,
        )
        steps = WorkbenchRunEnvelope.seed(name, jid, plan_steps)
        thread = threading.Thread(
            target=cls._background_job,
            args=(jid, name, norm, dict(api_settings), bool(force_refresh), plan_steps),
            daemon=True,
            name=f"wb-run-{jid[:8]}",
        )
        thread.start()
        return {
            "is_triggered": True,
            "job_id": jid,
            "run_id": jid,
            "steps": steps,
        }

    @classmethod
    def get_run_progress(
        cls,
        *,
        strategy_name: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        return WorkbenchRunEnvelope.get_run_progress(
            strategy_name=strategy_name, job_id=job_id
        )

    @classmethod
    def get_step_progress(
        cls,
        *,
        strategy_name: str,
        normalized_step: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        return WorkbenchRunEnvelope.get_step_progress(
            strategy_name=strategy_name,
            normalized_step=normalized_step,
            job_id=job_id,
        )

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
    def _plan_ui_steps(
        cls,
        strategy_name: str,
        norm_step: str,
        *,
        force_refresh: bool,
        runtime_settings: Dict[str, Any],
    ) -> List[str]:
        """Mirror Facade omit-enum rules for envelope step list."""
        kind = WorkbenchStep.parse(norm_step).to_simulate_kind()
        if kind == SimulateKind.ENUMERATE:
            return ["enum"]
        if force_refresh:
            return ["enum", norm_step]
        try:
            strategy_info = DiscoveryService.find_strategy(strategy_name)
            if strategy_info is None:
                return ["enum", norm_step]
            stock_list = GlobalEntityCache.get_stock_list()
            latest = GlobalEntityCache.get_latest_completed_trading_date()
            fp_res = FingerprintCalculator.calculate_fingerprints(
                strategy_info,
                runtime_settings,
                stock_list,
                latest,
            )
            cache_key = str(
                strategy_info.unique_relative_path or strategy_info.key or strategy_name
            )
            enum_ver = SimulationCacheManager.find_enum_output_version(cache_key, fp_res)
            if enum_ver:
                return [norm_step]
        except Exception:
            logger.exception("plan_ui_steps probe failed; defaulting to enum+target")
        return ["enum", norm_step]

    @classmethod
    def _background_job(
        cls,
        job_id: str,
        strategy_name: str,
        norm_step: str,
        api_settings: Dict[str, Any],
        force_refresh: bool,
        plan_steps: List[str],
    ) -> None:
        current_idx = 0
        lease = PipelineLease(
            kind="strategy_run",
            job_id=job_id,
            resource_key=strategy_name,
            label=f"strategy_run:{strategy_name}:{norm_step}",
            domains=["data", "strategy"],
        )
        try:
            lease.acquire()
        except PipelineLeaseBusyError as exc:
            WorkbenchRunEnvelope.fail(strategy_name, job_id, 0, str(exc))
            cls._clear_active(strategy_name, job_id)
            return

        try:
            WorkbenchRunEnvelope.mark_started(strategy_name, job_id)
            cls._duckdb_prepare()

            if plan_steps:
                WorkbenchRunEnvelope.on_substep_start(
                    strategy_name, job_id, 0, len(plan_steps), plan_steps[0]
                )

            kind = WorkbenchStep.parse(norm_step).to_simulate_kind()
            result = Strategy.simulate(
                strategy_name,
                kind=kind,
                ignore_cache=force_refresh,
                runtime_settings=api_settings,
            )
            wb_version = int((result or {}).get("_workbench_version") or 0)

            for idx, ui_step in enumerate(plan_steps):
                current_idx = idx
                if idx > 0:
                    WorkbenchRunEnvelope.on_substep_start(
                        strategy_name, job_id, idx, len(plan_steps), ui_step
                    )
                WorkbenchRunEnvelope.on_substep_finish(
                    strategy_name,
                    job_id,
                    idx,
                    len(plan_steps),
                    ui_step,
                    wb_version,
                )
            WorkbenchRunEnvelope.mark_phase_completed(strategy_name, job_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Workbench run failed job_id=%s", job_id)
            WorkbenchRunEnvelope.fail(strategy_name, job_id, current_idx, str(exc))
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
            from core.infra.db.engines.duckdb.process_pool_scope import (
                is_duckdb_backend,
                recover_after_worker_pool_interrupt,
            )

            if is_duckdb_backend():
                recover_after_worker_pool_interrupt()
        except Exception as exc:
            logger.warning("Workbench DuckDB prepare: %s", exc)

    @staticmethod
    def _duckdb_finalize() -> None:
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
            logger.warning("Workbench DuckDB finalize: %s", exc)


__all__ = ["WorkbenchRunLauncher"]
