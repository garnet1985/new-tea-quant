"""界面上的异步归因。后台跑战役，进度走 PipelineProgress，同一策略同时只跑一个任务。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.bff.APIs.strategy.routes.runner.workbench_run import WorkbenchRunLauncher
from core.infra.task_guard import TaskGuard
from core.infra.task_guard.contracts import TaskLeaseBusyError
from core.modules.strategy import Strategy
from core.modules.strategy.contracts import WorkbenchStep
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.progress import (
    ATTRIBUTE_PIPELINE,
    PipelineProgress,
)

logger = logging.getLogger(__name__)

_ATTR_DESC = {
    "enum": "枚举归因",
    "price": "价格归因",
    "portfolio": "组合归因",
}


class AttributeRunLauncher:
    """申请任务租约并在后台启动归因。"""

    @staticmethod
    def normalize_step(step: str) -> Optional[str]:
        """把步骤收成 enum、price 或 portfolio。"""
        parsed = WorkbenchStep.try_parse(step)
        return parsed.value if parsed is not None else None

    @staticmethod
    def pipeline_description(norm_step: str) -> str:
        """返回该层任务的中文说明。"""
        return _ATTR_DESC.get(str(norm_step or "").strip(), "归因")

    @classmethod
    def submit(
        cls,
        *,
        strategy_name: str,
        step: str,
        force_refresh: bool,
    ) -> Dict[str, Any]:
        """申请租约并在后台启动归因。"""
        name = str(strategy_name or "").strip()
        norm = cls.normalize_step(step)
        if not name:
            return {"is_triggered": False, "reason": "strategy_name 无效"}
        if norm is None:
            return {"is_triggered": False, "reason": "step 须为 enum / price / portfolio"}

        info = DiscoveryService.find_strategy(name)
        if info is None:
            return {"is_triggered": False, "reason": f"策略不存在或未启用: {name}"}

        gate = cls._gate(name, norm)
        if gate is not None:
            return {"is_triggered": False, "reason": gate}

        status = TaskGuard.read_status()
        if status.get("busy"):
            kind = status.get("kind") or "unknown"
            return {
                "is_triggered": False,
                "reason": f"系统任务进行中（{kind}），请稍后再试",
            }

        jid = f"attr-run-{uuid.uuid4().hex[:12]}"
        busy = WorkbenchRunLauncher.claim_active(name, jid)
        if busy:
            return {"is_triggered": False, "reason": busy}

        desc = cls.pipeline_description(norm)
        PipelineProgress.seed(
            name,
            jid,
            pipeline_name=ATTRIBUTE_PIPELINE,
            pipeline_description=desc,
        )
        thread = threading.Thread(
            target=cls._background_job,
            args=(jid, name, norm, bool(force_refresh)),
            daemon=True,
            name=f"attr-run-{jid[:8]}",
        )
        thread.start()
        return {
            "is_triggered": True,
            "job_id": jid,
            "run_id": jid,
            "pipeline_id": jid,
            "pipeline_name": ATTRIBUTE_PIPELINE,
            "pipeline_kind": "attribute",
            "pipeline_description": desc,
        }

    @classmethod
    def get_run_progress(
        cls,
        *,
        strategy_name: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        """读取一次归因任务的进度。"""
        return WorkbenchRunLauncher.get_run_progress(
            strategy_name=strategy_name, job_id=job_id
        )

    @classmethod
    def _gate(cls, strategy_name: str, norm_step: str) -> Optional[str]:
        """可跑则返回 None，否则返回给人看的原因。"""
        from core.bff.APIs.strategy.routes.attribution.status import (
            AttributeStatus,
        )

        status = AttributeStatus.probe(strategy_name, norm_step)
        if not status.get("visible"):
            return str(status.get("tooltip") or "请先完成本层回测再归因")
        if not status.get("enabled"):
            return str(status.get("tooltip") or "attribution.py 未就绪")
        return None

    @classmethod
    def _background_job(
        cls,
        job_id: str,
        strategy_name: str,
        norm_step: str,
        force_refresh: bool,
    ) -> None:
        lease = TaskGuard.lease(
            kind="strategy_attribute",
            job_id=job_id,
            resource_key=strategy_name,
            label=f"strategy_attribute:{strategy_name}:{norm_step}",
            domains=["data", "strategy"],
        )
        acquired = False
        try:
            lease.acquire()
            acquired = True
        except TaskLeaseBusyError as exc:
            inst = PipelineProgress.load(strategy_name, job_id)
            if inst is not None:
                inst.fail(str(exc))
            WorkbenchRunLauncher.release_active(strategy_name, job_id)
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Attribute lease acquire failed job_id=%s", job_id)
            inst = PipelineProgress.load(strategy_name, job_id)
            if inst is not None:
                inst.fail(str(exc))
            WorkbenchRunLauncher.release_active(strategy_name, job_id)
            return

        try:
            with PipelineProgress.bind(strategy_name, job_id) as prog:
                prog.mark_running()
                WorkbenchRunLauncher._duckdb_prepare()
                kind = WorkbenchStep.parse(norm_step).to_simulate_kind()
                if kind.value == "enum":
                    result = Strategy.attribute_enumerate(
                        strategy_name, ignore_cache=force_refresh
                    )
                elif kind.value == "price":
                    result = Strategy.attribute_price(
                        strategy_name, ignore_cache=force_refresh
                    )
                else:
                    result = Strategy.attribute_portfolio(
                        strategy_name, ignore_cache=force_refresh
                    )
                payload = {
                    "message": f"{cls.pipeline_description(norm_step)}已完成",
                    "group_id": str((result or {}).get("group_id") or "").strip()
                    or None,
                    "step": norm_step,
                    "layer": kind.value,
                    "headline": (result or {}).get("headline"),
                    "task_dir": (result or {}).get("task_dir"),
                    "report_path": (result or {}).get("report_path"),
                }
                prog.complete(result=payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Attribute run failed job_id=%s", job_id)
            inst = PipelineProgress.load(strategy_name, job_id)
            if inst is not None:
                inst.fail(str(exc))
            else:
                try:
                    with PipelineProgress.bind(strategy_name, job_id) as prog:
                        prog.fail(str(exc))
                except Exception:
                    logger.exception(
                        "PipelineProgress.fail unavailable job_id=%s", job_id
                    )
        finally:
            WorkbenchRunLauncher._duckdb_finalize()
            if acquired:
                try:
                    lease.release()
                except Exception:
                    logger.exception("attribute lease release failed")
            WorkbenchRunLauncher.release_active(strategy_name, job_id)


__all__ = ["AttributeRunLauncher"]
