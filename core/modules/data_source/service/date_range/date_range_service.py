"""
DateRangeService - 负责基于 renew 配置计算 last_update_map 和实体日期范围。

当前实现主要是对 DataSourceHandlerHelper 中现有逻辑的轻量封装，
为后续进一步对接 RenewManager / 各 renew services 预留统一入口。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set, Tuple

from core.modules.data_source.enums import UpdateMode
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.date_range import date_range_helper as drh
from core.infra.utils import Utils
def _period_sort_key(value: str, date_format: str) -> str:
    """Normalize DB/API values to a comparable period key for ``date_format``."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    period_type = Utils.date.normalize_period_type(date_format)
    if period_type == Utils.date.PERIOD_QUARTER and "Q" in raw.upper():
        return raw.upper().replace("-", "")
    if period_type == Utils.date.PERIOD_MONTH and len(raw) == 6 and raw.isdigit():
        return raw
    normalized = Utils.date.normalize_str(raw) or raw.replace("-", "").replace(" ", "")[:8]
    if not normalized:
        return raw
    if period_type == Utils.date.PERIOD_MONTH:
        return normalized[:6]
    if period_type == Utils.date.PERIOD_QUARTER:
        return Utils.date.to_period_str(normalized, period_type)
    return normalized[:8]


def _effective_end_period(effective_end: str, date_format: str) -> str:
    return _period_sort_key(effective_end, date_format)


def _entity_behind_effective_end(
    last_update: Optional[str],
    effective_end: str,
    date_format: str,
) -> bool:
    if not effective_end:
        return True
    if not last_update:
        return True
    return _period_sort_key(last_update, date_format) < _effective_end_period(
        effective_end, date_format
    )


def _range_has_work(start: str, end: str, date_format: str) -> bool:
    if not end:
        return True
    if not start:
        return True
    try:
        return _period_sort_key(start, date_format) <= _period_sort_key(end, date_format)
    except Exception:
        return str(start) <= str(end)


def _collect_entity_keys(context: Dict[str, Any], config: DataSourceConfig) -> Set[str]:
    keys: Set[str] = set()
    list_name = config.get_group_by_entity_list_name() or "stock_list"
    dependencies = context.get("dependencies") or {}
    entity_list = dependencies.get(list_name) or []
    key_field = config.get_group_by_key() or "id"
    terms = config.get_group_by_terms()
    group_fields = config.get_group_fields()
    is_multi = len(group_fields) > 1

    for entity_info in entity_list:
        if isinstance(entity_info, dict):
            entity_id = str(entity_info.get(key_field) or "").strip()
        else:
            entity_id = str(entity_info or "").strip()
        if not entity_id:
            continue
        if is_multi and terms:
            for term in terms:
                if term:
                    keys.add(f"{entity_id}::{str(term).lower()}")
        else:
            keys.add(entity_id)
    return keys


def _refresh_coverage_ok(
    *,
    source_key: str,
    context: Dict[str, Any],
    config: DataSourceConfig,
) -> bool:
    data_manager = context.get("data_manager")
    table_name = config.get_table_name()
    if not table_name or not data_manager:
        return False
    try:
        model = data_manager.get_table(table_name)
    except Exception:
        return False
    if not model:
        return False

    if source_key == "stock_list":
        try:
            return model.load_one("1=1") is not None
        except Exception:
            return False

    if source_key == "trade_calendar":
        effective_end = str(context.get("latest_completed_trading_date") or "").strip()
        if not effective_end:
            return False
        try:
            db_completed = model.load_db_latest_completed_trading_date(as_of_date=effective_end)
        except Exception:
            return False
        return bool(db_completed) and str(db_completed) == effective_end

    try:
        return model.load_one("1=1") is not None
    except Exception:
        return False


def needs_renew_work(
    context: Dict[str, Any],
    *,
    source_key: str,
) -> bool:
    """
    Whether the source is behind the effective data end and should renew.

    Uses the same ``DateRangeService`` inputs as the renew pipeline
    (``compute_last_update_map`` + ``compute_entity_date_ranges``). For
    incremental/rolling modes, compares DB latest period to effective end —
    not whether a rolling re-fetch window would run.
    """
    config = context.get("config")
    if not config or not hasattr(config, "get_renew_mode"):
        return True

    service = DateRangeService()
    last_update_map = service.compute_last_update_map(context)
    entity_ranges = service.compute_entity_date_ranges(context, last_update_map)
    renew_mode = config.get_renew_mode()
    date_format = config.get_date_format()
    effective_end = str(context.get("latest_completed_trading_date") or "").strip()

    if renew_mode == UpdateMode.REFRESH:
        if not entity_ranges:
            return False
        return not _refresh_coverage_ok(
            source_key=source_key,
            context=context,
            config=config,
        )

    if config.is_per_entity() or config.get_needs_stock_grouping():
        entity_keys = _collect_entity_keys(context, config)
        if not entity_keys:
            entity_keys = set(entity_ranges.keys())
        for entity_key in sorted(entity_keys):
            if _entity_behind_effective_end(
                last_update_map.get(entity_key),
                effective_end,
                date_format,
            ):
                return True
        return False

    if not entity_ranges:
        return False

    last_global = last_update_map.get("_global")
    if effective_end:
        return _entity_behind_effective_end(last_global, effective_end, date_format)

    return any(
        _range_has_work(start, end, date_format)
        for start, end in entity_ranges.values()
    )


class DateRangeService:
    """统一的日期范围计算服务（Phase 1 + Phase 2）。"""

    def compute_last_update_map(self, context: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Phase 1：获取所有实体的“原始” last_update 映射（不考虑 renew_mode）。

        当前直接委托 date_range_helper.compute_last_update_map，
        后续可以在这里接入 RenewManager 等更复杂策略。
        """
        return drh.compute_last_update_map(context)

    def compute_entity_date_ranges(
        self,
        context: Dict[str, Any],
        last_update_map: Dict[str, Optional[str]],
    ) -> Dict[str, Tuple[str, str]]:
        """
        Phase 2：基于 last_update 映射 + renew_mode + renew_if_over_days，
        计算本次需要抓取的实体及其 (start_date, end_date)。

        当前直接委托 date_range_helper.compute_entity_date_ranges，
        方便后续在不改 Handler 的前提下切换到 RenewManager / 各 RenewService。
        """
        return drh.compute_entity_date_ranges(context, last_update_map)

