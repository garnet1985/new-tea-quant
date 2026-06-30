"""Tag entity_timeline 执行流水线。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, TYPE_CHECKING, Type

from core.modules.tag.engines.shared.backend import backend_is_duckdb
from core.modules.tag.engines.timeline.job_builder import build_timeline_jobs
from core.modules.tag.models.scenario_model import ScenarioModel

if TYPE_CHECKING:
    from core.modules.tag.engines.shared.base_worker import BaseTagWorker

logger = logging.getLogger(__name__)


def run_timeline_pipeline(
    mgr: Any,
    *,
    scenario_model: ScenarioModel,
    entity_list: List[str],
    settings: Dict[str, Any],
    worker_class: "Type[BaseTagWorker]",
    tag_key: str,
) -> None:
    """Tag timeline 执行流水线（BacktestEngine 版）。

    变更：
    - 探针、规划、切割、执行 → 全部交给 BacktestEngine
    - Tag 只负责：构建 jobs + 积攒入库 + 进度上报
    """
    from core.modules.tag.services.execution.tag_job_pipeline import (
        run_tag_timeline_via_backtest_engine,
    )

    scenario_name = scenario_model.get_name()
    performance = dict(settings.get("performance") or {})
    performance.update(mgr._dispatch_overrides)
    scenario_cache = mgr.scenario_cache.get(tag_key) or {}

    # DuckDB 主进程数据库恢复（在 engine.run 之前）
    if backend_is_duckdb(mgr.data_mgr) and getattr(mgr.data_mgr, "db", None) is None:
        from core.infra.db.engines.duckdb.process_pool_scope import (
            resume_main_database_with_retry,
        )
        resume_main_database_with_retry(mgr.data_mgr)
        mgr.tag_data_service = mgr.data_mgr.stock.tags

    # 构建 timeline jobs（业务逻辑，Tag 负责）
    jobs = build_timeline_jobs(
        entity_list=entity_list,
        settings=settings,
        scenario_model=scenario_model,
        scenario_cache=scenario_cache,
        tag_data_service=mgr.tag_data_service,
        dcm=mgr._data_contract_manager,
    )

    if not jobs:
        logger.warning("没有新的计算任务，跳过执行: scenario=%s", scenario_name)
        return None

    # 交给 BacktestEngine 执行
    return run_tag_timeline_via_backtest_engine(
        timeline_jobs=jobs,
        settings={**settings, "scenario_name": scenario_name, "performance": performance},
        run_name=f"tag:{scenario_name}",
        total_entities=len(entity_list),
        on_pipeline_progress=getattr(mgr, "_pipeline_progress_callback", None),
        duckdb_data_mgr=mgr.data_mgr,
    )
