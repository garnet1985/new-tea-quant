"""Tag batch stage：bulk kline / prior，按 entity 拆分 inject。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_manager import DataManager
from core.modules.tag.components.job_staging.tag_prior_values import fetch_prior_tag_values_batch
from core.modules.data_contract.kline_keys import (
    is_stock_kline_data_id_value,
    kline_term_from_data_id_value,
)
from core.utils.date.date_utils import DateUtils


def kline_declaration_from_settings(
    settings: Dict[str, Any],
) -> Tuple[str, str, str]:
    """从 scenario settings 解析 K 线 data_id / term / adjust。"""
    for item in (settings.get("data") or {}).get("required") or []:
        data_id = str(item.get("data_id") or "").strip()
        if not is_stock_kline_data_id_value(data_id):
            continue
        params = dict(item.get("params") or {})
        term = kline_term_from_data_id_value(data_id)
        adjust = str(params.get("adjust") or "qfq").lower()
        return data_id, term, adjust
    return "stock.kline.daily", "daily", "qfq"


def kline_params_from_settings(settings: Dict[str, Any]) -> Tuple[str, str]:
    """兼容旧调用：返回 (term, adjust)。"""
    _, term, adjust = kline_declaration_from_settings(settings)
    return term, adjust


def trading_dates_from_rows(
    rows: List[Dict[str, Any]],
    *,
    start_date: str,
    end_date: str,
    time_field: str = "date",
) -> List[str]:
    all_dates = sorted(
        {
            DateUtils.normalize(r.get(time_field), fmt=DateUtils.FMT_YYYYMMDD)
            for r in (rows or [])
            if r.get(time_field)
        }
    )
    all_dates = [d for d in all_dates if d]
    if not all_dates:
        return []
    left = start_date or all_dates[0]
    right = end_date or all_dates[-1]
    max_date = all_dates[-1]
    if right and max_date and right > max_date:
        right = max_date
    return [d for d in all_dates if left <= d <= right]


def stage_entities_batch(
    *,
    data_mgr: DataManager,
    entities: List[Dict[str, Any]],
    settings: Dict[str, Any],
    tag_definition_ids: List[int],
) -> Dict[str, Dict[str, Any]]:
    """
    一次 bulk IO，返回 entity_id → inject 切片（slot_data / trading_dates / prior）。
    """
    if not entities:
        return {}

    entity_ids = [str(e["entity_id"]) for e in entities if e.get("entity_id")]
    starts = [str(e.get("start_date") or "") for e in entities if e.get("start_date")]
    ends = [str(e.get("end_date") or "") for e in entities if e.get("end_date")]
    batch_start = min(starts) if starts else ""
    batch_end = max(ends) if ends else ""

    kline_slot, term, adjust = kline_declaration_from_settings(settings)
    kline_by_id = data_mgr.stock.kline.load_batch(
        entity_ids,
        term=term,
        start_date=batch_start or None,
        end_date=batch_end or None,
        adjust=adjust,
    )

    prior_by_id = fetch_prior_tag_values_batch(
        data_mgr.stock.tags,
        entity_ids=entity_ids,
        tag_definition_ids=tag_definition_ids,
    )

    time_field = "date"
    out: Dict[str, Dict[str, Any]] = {}
    for ent in entities:
        eid = str(ent.get("entity_id") or "")
        if not eid:
            continue
        rows = list(kline_by_id.get(eid) or [])
        out[eid] = {
            "slot_data": {kline_slot: rows},
            "trading_dates": trading_dates_from_rows(
                rows,
                start_date=str(ent.get("start_date") or ""),
                end_date=str(ent.get("end_date") or ""),
                time_field=time_field,
            ),
            "time_field_overrides": {kline_slot: time_field},
            "prior_tag_values": dict(prior_by_id.get(eid) or {}),
        }
    return out
