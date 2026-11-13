"""Evaluate data source update status for UI catalog."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.infra.project_context import ProjectContext

from core.modules.data_source.core.data_class.config import DataSourceConfig
from core.modules.data_source.core.data_class.handler_mapping import HandlerMapping
from core.modules.data_source.core.service.date_range.date_range_service import needs_renew_work
from core.modules.data_manager import DataManager


def _demo_truncation_meta() -> Tuple[bool, str, str]:
    """演示档提示：区间由官网决定，本地不硬编码截止日。"""
    try:
        from core.modules.ntq_external.member_profile import member_profile

        profile = member_profile()
    except Exception:
        return False, "", ""
    if profile.get("sync_access") != "demo":
        return False, "", ""
    return (
        True,
        "当前会员档可下载区间由官网决定；完整续传需 Pro（或等价点数）档位。",
        "/settings/membership",
    )


def get_data_end_meta_light() -> Dict[str, Any]:
    """假定最新日展示 + 演示档提示；不做日历/DB 查询（快列）。"""
    assumed = ProjectContext.config.get_assumed_latest_completed_trading_date()
    is_truncated, hint, settings_path = _demo_truncation_meta()
    return {
        "assumed_latest_completed_trading_date": assumed,
        "effective_end_date": None,
        "is_end_date_truncated": is_truncated,
        "truncation_hint": hint,
        "truncation_settings_path": settings_path or None,
    }


def _resolve_freshness_end_date(data_manager) -> str:
    """计划和“是否还要更新”共用的截止数据日（日历；不按本地会员窗裁）。"""
    from core.modules.data_source.core.service.renew_progress import resolve_uptodate_day

    return resolve_uptodate_day(data_manager)


def get_data_end_meta(data_manager) -> Dict[str, Any]:
    """Summarize renew effective end date；assumed 仅作计算侧展示。"""
    assumed = ProjectContext.config.get_assumed_latest_completed_trading_date()
    effective_end = _resolve_freshness_end_date(data_manager)
    is_truncated, hint, settings_path = _demo_truncation_meta()

    return {
        "assumed_latest_completed_trading_date": assumed,
        "effective_end_date": effective_end or None,
        "is_end_date_truncated": is_truncated,
        "truncation_hint": hint,
        "truncation_settings_path": settings_path or None,
    }


def _build_freshness_context(
    *,
    source_key: str,
    config: DataSourceConfig,
    mappings: HandlerMapping,
    data_manager,
) -> Dict[str, Any]:
    latest = _resolve_freshness_end_date(data_manager)
    dependencies: Dict[str, Any] = {}
    for dep in mappings.get_depend_on_data_source_names(source_key):
        if dep == "latest_completed_trading_date":
            dependencies[dep] = latest
        elif dep == "stock_list":
            try:
                rows = data_manager.stock.list.load_all()
                dependencies[dep] = DataManager.sample_universe.slice_stock_list(rows or [])
            except Exception:
                dependencies[dep] = []
        elif dep == "index_list":
            try:
                dependencies[dep] = data_manager.index.load_list(sync_from_config=False)
            except Exception:
                dependencies[dep] = []
        elif dep == "sw_industry":
            try:
                dependencies[dep] = data_manager.sw.load_quote_list() or []
            except Exception:
                dependencies[dep] = []

    return {
        "config": config,
        "data_manager": data_manager,
        "latest_completed_trading_date": latest,
        "dependencies": dependencies,
    }


def evaluate_update_status(
    *,
    source_key: str,
    config: DataSourceConfig,
    mappings: HandlerMapping,
    data_manager,
) -> Tuple[str, str, str]:
    """
    Return ``(update_status, update_status_label, update_status_hint)``.

    Delegates to ``needs_renew_work`` — the same renew date-range stack the pipeline uses.
    """
    if not data_manager:
        return "needs_update", "需要更新", ""

    try:
        context = _build_freshness_context(
            source_key=source_key,
            config=config,
            mappings=mappings,
            data_manager=data_manager,
        )
        if needs_renew_work(context, source_key=source_key):
            _, hint, _ = _demo_truncation_meta()
            return "needs_update", "需要更新", hint
        return "up_to_date", "已经更新", ""
    except Exception:
        return "needs_update", "需要更新", ""
