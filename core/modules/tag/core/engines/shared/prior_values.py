"""Tag prior value 预取（incremental 变化检测暖启动）。

消费者: TagEntityJobBuilder
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.data_manager.data_services.stock.sub_services.tag_service import (
        TagDataService,
    )

logger = logging.getLogger(__name__)


class TagPriorValues:
    """按 entity / tag_definition 取最新 json_value 并解析标量。"""

    _BATCH_SQL = """
        SELECT entity_id, tag_definition_id, json_value
        FROM (
            SELECT entity_id, tag_definition_id, json_value,
                   ROW_NUMBER() OVER (
                       PARTITION BY entity_id, tag_definition_id
                       ORDER BY as_of_date DESC
                   ) AS rn
            FROM sys_tag_value
            WHERE entity_id IN ({entity_placeholders})
              AND tag_definition_id IN ({tag_placeholders})
        ) t
        WHERE rn = 1
    """

    @classmethod
    def fetch_batch(
        cls,
        tag_service: "TagDataService",
        *,
        entity_ids: List[str],
        tag_definition_ids: List[int],
    ) -> Dict[str, Dict[str, Any]]:
        """主进程：一批 entity 一次 SQL → ``{entity_id: {def_id: json_value}}``。"""
        ids = [str(e) for e in entity_ids if e]
        td_ids = [int(x) for x in tag_definition_ids if x is not None]
        if not ids or not td_ids:
            return {}
        e_ph = ",".join(["%s"] * len(ids))
        t_ph = ",".join(["%s"] * len(td_ids))
        sql = cls._BATCH_SQL.format(
            entity_placeholders=e_ph, tag_placeholders=t_ph
        )
        params = tuple(ids) + tuple(td_ids)
        try:
            rows = tag_service.db.execute_sync_query_for_table(
                "sys_tag_value",
                sql,
                params,
            )
        except Exception as exc:
            logger.warning(
                "批量预取 prior tag_value 失败: entities=%d err=%s",
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

    @classmethod
    def parse_scalar(
        cls, raw: Any, *, default: Optional[str] = None
    ) -> Optional[str]:
        """从 json_value 解析标量字符串（如市值档位）。"""
        if raw is None or raw == "":
            return default
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return default
            if text.startswith("{"):
                try:
                    payload = json.loads(text)
                except Exception:
                    return text
                if isinstance(payload, dict):
                    inner = payload.get("value")
                    if inner is not None:
                        return str(inner).strip() or default
                return default
            return text
        if isinstance(raw, dict):
            inner = raw.get("value")
            if inner is not None:
                return str(inner).strip() or default
        return default


__all__ = ["TagPriorValues"]
