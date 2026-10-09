"""界面上的异步滚动对照。进度按窗口里的枚举、价格、资金各记一次。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.bff.APIs.strategy.routes.runner.workbench_run import WorkbenchRunLauncher
from core.infra.task_guard import TaskGuard
from core.infra.task_guard.contracts import TaskLeaseBusyError
from core.modules.strategy import Strategy
from core.modules.strategy.core.engines.rolling.readiness import probe
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.progress import (
    ROLLING_PIPELINE,
    PipelineProgress,
)

logger = logging.getLogger(__name__)


class RollingRunLauncher:
    """申请任务租约并在后台启动滚动对照。"""

    @classmethod
    def submit(cls, *, strategy_name: str, force_refresh: bool) -> Dict[str, Any]:
        """申请租约并在后台启动滚动对照。"""
        name = str(strategy_name or "").strip()
        if not name:
            return {"is_triggered": False, "reason": "strategy_name 无效"}
        if DiscoveryService.find_strategy(name) is None:
            return {"is_triggered": False, "reason": f"策略不存在或未启用: {name}"}

        gate = cls._gate(name)
        if gate is not None:
            return {"is_triggered": False, "reason": gate}

        status = TaskGuard.read_status()
        if status.get("busy"):
            kind = status.get("kind") or "unknown"
            return {
                "is_triggered": False,
                "reason": f"系统任务进行中（{kind}），请稍后再试",
            }

        jid = f"roll-run-{uuid.uuid4().hex[:12]}"
        busy = WorkbenchRunLauncher.claim_active(name, jid)
        if busy:
            return {"is_triggered": False, "reason": busy}

        desc = PipelineProgress.pipeline_description(ROLLING_PIPELINE)
        PipelineProgress.seed(
            name,
            jid,
            pipeline_name=ROLLING_PIPELINE,
            pipeline_description=desc,
        )
        thread = threading.Thread(
            target=cls._background_job,
            args=(jid, name, bool(force_refresh)),
            daemon=True,
            name=f"roll-run-{jid[:8]}",
        )
        thread.start()
        return {
            "is_triggered": True,
            "job_id": jid,
            "run_id": jid,
            "pipeline_id": jid,
            "pipeline_name": ROLLING_PIPELINE,
            "pipeline_kind": "rolling",
            "pipeline_description": desc,
        }

    @classmethod
    def get_run_progress(
        cls,
        *,
        strategy_name: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        """读取一次滚动对照任务的进度。"""
        return WorkbenchRunLauncher.get_run_progress(
            strategy_name=strategy_name, job_id=job_id
        )

    @classmethod
    def _gate(cls, strategy_name: str) -> Optional[str]:
        """可跑则返回 None，否则返回给人看的原因。"""
        status = probe(strategy_name)
        if not status.get("enabled"):
            return str(status.get("tooltip") or "滚动对照还不能开始")
        return None

    @classmethod
    def _background_job(
        cls,
        job_id: str,
        strategy_name: str,
        force_refresh: bool,
    ) -> None:
        lease = TaskGuard.lease(
            kind="strategy_rolling",
            job_id=job_id,
            resource_key=strategy_name,
            label=f"strategy_rolling:{strategy_name}",
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
        except (OSError, ValueError, RuntimeError) as exc:
            logger.exception("Rolling lease acquire failed job_id=%s", job_id)
            inst = PipelineProgress.load(strategy_name, job_id)
            if inst is not None:
                inst.fail(str(exc))
            WorkbenchRunLauncher.release_active(strategy_name, job_id)
            return

        try:
            with PipelineProgress.bind(strategy_name, job_id) as prog:
                prog.mark_running()
                WorkbenchRunLauncher._duckdb_prepare()
                result = Strategy.rolling(strategy_name, ignore_cache=force_refresh)
                payload = {
                    "message": "滚动对照已完成",
                    "parent_version_id": str(
                        (result or {}).get("parent_version_id") or ""
                    ).strip()
                    or None,
                    "report_path": (result or {}).get("report_path"),
                    "window_count": (result or {}).get("window_count"),
                }
                prog.complete(result=payload)
        except Exception as exc:  # noqa: BLE001 — 后台线程必须把失败写进进度
            logger.exception("Rolling run failed job_id=%s", job_id)
            inst = PipelineProgress.load(strategy_name, job_id)
            if inst is not None:
                inst.fail(str(exc))
        finally:
            WorkbenchRunLauncher._duckdb_finalize()
            if acquired:
                try:
                    lease.release()
                except (OSError, RuntimeError):
                    logger.exception("rolling lease release failed")
            WorkbenchRunLauncher.release_active(strategy_name, job_id)


__all__ = ["RollingRunLauncher"]
