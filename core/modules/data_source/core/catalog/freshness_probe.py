"""Evaluate data source update status for UI catalog."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from core.infra.project_context import ProjectContext

from core.modules.data_source.core.data_class.config import DataSourceConfig
from core.modules.data_source.core.data_class.handler_mapping import HandlerMapping
from core.modules.data_source.core.service.date_range.date_range_service import needs_renew_work
from core.modules.data_manager import DataManager


def _format_yyyy_mm_dd(value: str) -> str:
    raw = str(value or "").strip().replace("-", "")
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return str(value or "").strip()


def _truncation_meta(configured_as_of: str) -> Tuple[bool, str, str]:
    is_truncated = bool(configured_as_of)
    hint = ""
    settings_path = ""
    if is_truncated:
        settings_path = "/settings/data"
        hint = (
            f"data.json 已将数据截至日期截断为 {_format_yyyy_mm_dd(configured_as_of)}"
            f"（as_of_latest_completed_trading_date）。"
            "更新状态按该截至日评估，而非实时市场最新交易日。"
        )
    return is_truncated, hint, settings_path


def get_data_end_meta_light() -> Dict[str, Any]:
    """``data.json`` truncation only — no DB / calendar lookup (fast list)."""
    configured_as_of = ProjectContext.config.get_as_of_latest_completed_trading_date()
    is_truncated, hint, settings_path = _truncation_meta(configured_as_of)
    return {
        "configured_as_of": configured_as_of,
        "effective_end_date": None,
        "is_end_date_truncated": is_truncated,
        "truncation_hint": hint,
        "truncation_settings_path": settings_path or None,
    }


def _resolve_freshness_end_date(data_manager) -> str:
    """
    计划和“是否还要更新”共用的截止数据日。

    data.json 的 as_of 先落到该日或之前最近的开市日，再被会员能拿到的最后一天挡住。
    """
    from core.modules.data_source.core.service.renew_progress import resolve_uptodate_day

    return resolve_uptodate_day(data_manager)


def get_data_end_meta(data_manager) -> Dict[str, Any]:
    """Summarize effective data end date and ``data.json`` truncation."""
    configured_as_of = ProjectContext.config.get_as_of_latest_completed_trading_date()
    effective_end = _resolve_freshness_end_date(data_manager)
    is_truncated, hint, settings_path = _truncation_meta(configured_as_of)

    return {
        "configured_as_of": configured_as_of,
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
            hint = ""
            if ProjectContext.config.get_as_of_latest_completed_trading_date():
                _, truncation_hint, _ = _truncation_meta(
                    ProjectContext.config.get_as_of_latest_completed_trading_date()
                )
                hint = truncation_hint
            return "needs_update", "需要更新", hint
        return "up_to_date", "已经更新", ""
    except Exception:
        return "needs_update", "需要更新", ""
