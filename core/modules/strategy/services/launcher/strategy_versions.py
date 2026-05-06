"""Workbench snapshot versions for UI dropdowns（对比 / 恢复目标）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager

# 与 ``API.md`` V2-03：固定至多 10 条，不分页。
DROPDOWN_LIMIT = 10


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat(sep=" ", timespec="seconds")
    return str(dt)


def fetch_strategy_versions_dropdown(strategy_name: str) -> List[Dict[str, Any]]:
    """
    返回某策略工作台快照版本列表（最多 ``DROPDOWN_LIMIT`` 条，从新到旧）。

    无表或无行时返回空列表。
    """
    name = str(strategy_name or "").strip()
    if not name:
        return []

    model = DataManager().get_table("sys_strategy_workbench_snapshot")
    if model is None:
        return []

    rows = model.list_by_strategy(name, limit=DROPDOWN_LIMIT)
    items: List[Dict[str, Any]] = []
    for row in rows:
        sid = int(row.get("snapshot_id") or row.get("version") or 0)
        if sid <= 0:
            continue
        items.append(
            {
                "version_id": f"v{sid}",
                "snapshot_id": sid,
                "updated_at": _iso(row.get("updated_at")),
                "created_at": _iso(row.get("created_at")),
            }
        )
    return items
