"""主进程预取 prior tag_value；Worker inject 模式读取，避免子进程触 tag 库。"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.data_manager.data_services.stock.sub_services.tag_service import TagDataService

logger = logging.getLogger(__name__)

_LATEST_TAG_VALUE_SQL = """
    SELECT json_value
    FROM sys_tag_value
    WHERE entity_id = %s AND tag_definition_id = %s
    ORDER BY as_of_date DESC
    LIMIT 1
"""

_PRIOR_BATCH_SQL = """
    SELECT entity_id, tag_definition_id, json_value
    FROM (
        SELECT entity_id, tag_definition_id, json_value,
               ROW_NUMBER() OVER (
                   PARTITION BY entity_id, tag_definition_id ORDER BY as_of_date DESC
               ) AS rn
        FROM sys_tag_value
        WHERE entity_id IN ({entity_placeholders})
          AND tag_definition_id IN ({tag_placeholders})
    ) t
    WHERE rn = 1
"""


def fetch_prior_tag_values_batch(
    tag_service: "TagDataService",
    *,
    entity_ids: List[str],
    tag_definition_ids: List[int],
) -> Dict[str, Dict[str, Any]]:
    """主进程：一批 entity 一次 SQL 取各 tag 最新 json_value。"""
    ids = [str(e) for e in entity_ids if e]
    td_ids = [int(x) for x in tag_definition_ids if x is not None]
    if not ids or not td_ids:
        return {}
    e_ph = ",".join(["%s"] * len(ids))
    t_ph = ",".join(["%s"] * len(td_ids))
    sql = _PRIOR_BATCH_SQL.format(entity_placeholders=e_ph, tag_placeholders=t_ph)
    params = tuple(ids) + tuple(td_ids)
    try:
        rows = tag_service.db.execute_sync_query_for_table(
            "sys_tag_value",
            sql,
            params,
        )
    except Exception as exc:
        logger.warning(
            "stage 批量预取 prior tag_value 失败: entities=%d err=%s",
            len(ids),
            exc,
        )
        return {}
    out: Dict[str, Dict[str, Any]] = {eid: {} for eid in ids}
    for row in rows or []:
        eid = str(row.get("entity_id") or "")
        td = row.get("tag_definition_id")
        if eid in out and td is not None:
            out[eid][str(int(td))] = row.get("json_value")
    return out


def fetch_prior_tag_values(
    tag_service: "TagDataService",
    *,
    entity_id: str,
    tag_definition_ids: List[int],
) -> Dict[str, Any]:
    """主进程：按 tag_definition 取该 entity 最新 json_value。"""
    out: Dict[str, Any] = {}
    for td_id in tag_definition_ids:
        try:
            rows = tag_service.db.execute_sync_query_for_table(
                "sys_tag_value",
                _LATEST_TAG_VALUE_SQL,
                (entity_id, int(td_id)),
            )
            if rows:
                out[str(td_id)] = rows[0].get("json_value")
        except Exception as exc:
            logger.warning(
                "stage 预取 prior tag_value 失败: entity=%s tag_definition_id=%s err=%s",
                entity_id,
                td_id,
                exc,
            )
    return out


def load_latest_tag_value_json(
    job_payload: Dict[str, Any],
    tag_data_service: Optional["TagDataService"],
    *,
    entity_id: str,
    tag_definition_id: int,
) -> Optional[Any]:
    """Worker：优先读 inject.prior_tag_values，否则非 inject 模式走 DB。"""
    inject = job_payload.get("_inject") or {}
    prior = inject.get("prior_tag_values") or {}
    key = str(tag_definition_id)
    if key in prior:
        return prior[key]
    if tag_data_service is None:
        return None
    rows = tag_data_service.db.execute_sync_query_for_table(
        "sys_tag_value",
        _LATEST_TAG_VALUE_SQL,
        (entity_id, int(tag_definition_id)),
    )
    if not rows:
        return None
    return rows[0].get("json_value")


def parse_tag_value_bool(raw: Any, *, default: bool = False) -> bool:
    """从 json_value 字段解析布尔状态。"""
    if raw is None or raw == "":
        return default
    try:
        if isinstance(raw, dict):
            payload = raw
        elif isinstance(raw, str):
            payload = json.loads(raw)
        else:
            payload = {}
        value = payload.get("value")
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
    except Exception:
        return default
    return default
