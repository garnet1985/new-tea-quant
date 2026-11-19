"""Register JobPipeline kind handlers (BFF process)."""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.infra.job_pipeline import JobPipeline

logger = logging.getLogger(__name__)

# 一键 renew 入队时的占位 resource_key（空源列表无法当 key）
DATA_RENEW_ALL_RESOURCE = "*"


def register_job_pipeline_handlers() -> None:
    JobPipeline.register_handler("strategy_run", _handle_strategy_run)
    JobPipeline.register_handler("strategy_attribute", _handle_strategy_attribute)
    JobPipeline.register_handler("strategy_rolling", _handle_strategy_rolling)
    JobPipeline.register_handler("tag_run", _handle_tag_run)
    JobPipeline.register_handler("data_renew", _handle_data_renew)
    JobPipeline.register_handler("import_data", _handle_import_data)


def _handle_strategy_run(job: Dict[str, Any]) -> Dict[str, Any]:
    from core.bff.APIs.strategy.routes.runner.workbench_run import WorkbenchRunLauncher

    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    name = str(job.get("resource_key") or "").strip()
    step = str(payload.get("step") or "").strip()
    settings = payload.get("api_settings")
    if not isinstance(settings, dict):
        settings = {}
    return WorkbenchRunLauncher.start_now(
        strategy_name=name,
        step=step,
        api_settings=settings,
        force_refresh=bool(payload.get("force_refresh")),
        expected_rev=payload.get("expected_rev"),
        force_settings_write=bool(payload.get("force_settings_write")),
    )


def _handle_strategy_attribute(job: Dict[str, Any]) -> Dict[str, Any]:
    from core.bff.APIs.strategy.routes.attribution.attribute_run import (
        AttributeRunLauncher,
    )

    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    name = str(job.get("resource_key") or "").strip()
    step = str(payload.get("step") or "").strip()
    return AttributeRunLauncher.start_now(
        strategy_name=name,
        step=step,
        force_refresh=bool(payload.get("force_refresh")),
    )


def _handle_strategy_rolling(job: Dict[str, Any]) -> Dict[str, Any]:
    from core.bff.APIs.strategy.routes.rolling.rolling_run import RollingRunLauncher

    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    name = str(job.get("resource_key") or "").strip()
    return RollingRunLauncher.start_now(
        strategy_name=name,
        force_refresh=bool(payload.get("force_refresh")),
    )


def _handle_tag_run(job: Dict[str, Any]) -> Dict[str, Any]:
    from core.modules.tag import Tag

    name = str(job.get("resource_key") or "").strip()
    return Tag.start_run(tag_key=name)


def _handle_data_renew(job: Dict[str, Any]) -> Dict[str, Any]:
    from core.bff.APIs.data.sources.renew_launcher import DataRenewLauncher

    resource = str(job.get("resource_key") or "").strip()
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    source = str(payload.get("source") or "").strip()
    if not source and resource not in ("", DATA_RENEW_ALL_RESOURCE):
        source = resource
    return DataRenewLauncher.start_now(source or None)


def _handle_import_data(job: Dict[str, Any]) -> Dict[str, Any]:
    from core.bff.APIs.platform.setup.import_data_launcher import ImportDataLauncher

    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    pack_kind = str(payload.get("pack_kind") or "demo").strip().lower() or "demo"
    return ImportDataLauncher.start_now(
        pack_kind=pack_kind,
        force=bool(payload.get("force")),
    )
