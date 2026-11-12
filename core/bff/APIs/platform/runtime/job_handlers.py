"""Register JobPipeline kind handlers (BFF process)."""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.infra.job_pipeline import JobPipeline

logger = logging.getLogger(__name__)


def register_job_pipeline_handlers() -> None:
    JobPipeline.register_handler("strategy_run", _handle_strategy_run)


def _handle_strategy_run(job: Dict[str, Any]) -> Dict[str, Any]:
    from core.bff.APIs.strategy.routes.runner.workbench_run import WorkbenchRunLauncher

    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    name = str(job.get("resource_key") or "").strip()
    step = str(payload.get("step") or "").strip()
    settings = payload.get("api_settings")
    if not isinstance(settings, dict):
        settings = {}
    return WorkbenchRunLauncher.submit(
        strategy_name=name,
        step=step,
        api_settings=settings,
        force_refresh=bool(payload.get("force_refresh")),
        expected_rev=payload.get("expected_rev"),
        force_settings_write=bool(payload.get("force_settings_write")),
        allow_enqueue=False,
    )
