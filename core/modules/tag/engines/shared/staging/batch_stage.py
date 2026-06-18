"""Tag batch stage：按 scenario 声明 bulk 装填 PER_ENTITY 数据，按 entity 拆分 inject。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.data_contract.kline_keys import (
    is_stock_kline_data_id_value,
    kline_term_from_data_id_value,
)
from core.modules.data_manager import DataManager
from core.modules.tag.engines.shared.staging.prior_values import fetch_prior_tag_values_batch
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


def per_entity_declarations(
    settings: Dict[str, Any],
    *,
    dcm: DataContractManager,
) -> List[Dict[str, Any]]:
    """``data.required`` 中 scope=PER_ENTITY 的声明列表。"""
    out: List[Dict[str, Any]] = []
    for item in (settings.get("data") or {}).get("required") or []:
        raw = str(item.get("data_id") or "").strip()
        if not raw:
            continue
        spec = dcm.map.get(DataKey(raw))
        if spec and spec.get("scope") == ContractScope.PER_ENTITY:
            out.append(dict(item))
    return out


def axis_slot_from_settings(
    settings: Dict[str, Any],
    declarations: List[Dict[str, Any]],
) -> str:
    configured = str((settings.get("data") or {}).get("tag_time_axis_based_on") or "").strip()
    if configured:
        return configured
    if declarations:
        return str(declarations[0].get("data_id") or "").strip()
    return "stock.kline.daily"


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

    按 ``settings.data.required`` 装填所有 PER_ENTITY 数据源（不仅限于 K 线）。
    """
    if not entities:
        return {}

    entity_ids = [str(e["entity_id"]) for e in entities if e.get("entity_id")]
    starts = [str(e.get("start_date") or "") for e in entities if e.get("start_date")]
    ends = [str(e.get("end_date") or "") for e in entities if e.get("end_date")]
    batch_start = min(starts) if starts else ""
    batch_end = max(ends) if ends else ""

    contract_cache = ContractCacheManager()
    contract_cache.enter_strategy_run()
    dcm = DataContractManager(contract_cache=contract_cache)
    declarations = per_entity_declarations(settings, dcm=dcm)
    if not declarations:
        kline_slot, term, adjust = kline_declaration_from_settings(settings)
        declarations = [{"data_id": kline_slot, "params": {"adjust": adjust}}]

    axis_slot = axis_slot_from_settings(settings, declarations)
    slot_maps: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        eid: {} for eid in entity_ids
    }

    for item in declarations:
        raw = str(item.get("data_id") or "").strip()
        if not raw:
            continue
        slot = raw
        params = dict(item.get("params") or {})

        if is_stock_kline_data_id_value(slot):
            term = kline_term_from_data_id_value(slot)
            adjust = str(params.get("adjust") or "qfq").lower()
            by_id = data_mgr.stock.kline.load_batch(
                entity_ids,
                term=term,
                start_date=batch_start or None,
                end_date=batch_end or None,
                adjust=adjust,
            )
            for eid in entity_ids:
                slot_maps[eid][slot] = list(by_id.get(eid) or [])
            continue

        issued = dcm.issue(
            DataKey(slot),
            entity_ids=entity_ids,
            start=batch_start or None,
            end=batch_end or None,
            **params,
        )
        for eid, contract in (issued.by_entity or {}).items():
            slot_maps[eid][slot] = list(contract.data or [])

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
        slots = slot_maps.get(eid) or {}
        axis_rows = list(slots.get(axis_slot) or [])
        out[eid] = {
            "slot_data": slots,
            "trading_dates": trading_dates_from_rows(
                axis_rows,
                start_date=str(ent.get("start_date") or ""),
                end_date=str(ent.get("end_date") or ""),
                time_field=time_field,
            ),
            "time_field_overrides": {key: time_field for key in slots},
            "prior_tag_values": dict(prior_by_id.get(eid) or {}),
        }
    return out
