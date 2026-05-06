"""V2-07：按 step 读取快照 ``result_report`` 中对应槽位的报告。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.data_manager import DataManager

# 与 ``SimulatorResDbCacheService`` / ``result_report`` 聚合键一致
_STEP_TO_SLOT = {
    "enum": "enum",
    "price": "price_factor",
    "capital": "capital_allocation",
}


def step_to_report_slot(normalized_step: str) -> Optional[str]:
    return _STEP_TO_SLOT.get(normalized_step)


def parse_snapshot_id(version_id: str) -> Optional[int]:
    """接受 ``v3`` / ``3`` 等形式。"""
    s = str(version_id or "").strip()
    if not s:
        return None
    if s.lower().startswith("v"):
        s = s[1:]
    try:
        n = int(s)
        return n if n > 0 else None
    except ValueError:
        return None


def build_step_report_message(
    *,
    strategy_name: str,
    normalized_step: str,
    snapshot_id: int,
) -> Optional[Dict[str, Any]]:
    """
    读 ``sys_strategy_workbench_snapshot`` 一行，取出该 step 槽位报告。
    行不存在返回 ``None``。
    """
    slot = step_to_report_slot(normalized_step)
    if not slot:
        return None

    model = DataManager().get_table("sys_strategy_workbench_snapshot")
    if model is None:
        return None

    name = str(strategy_name).strip()
    row = model.load_by_strategy_snapshot_id(name, int(snapshot_id))
    if not row:
        return None

    rr = row.get("result_report") or {}
    raw = rr.get(slot)
    if raw is None:
        report: Any = {}
    elif isinstance(raw, dict):
        report = raw
    else:
        report = raw

    return {
        "version_id": f"v{int(snapshot_id)}",
        "strategy_name": name,
        "step": normalized_step,
        "report": report,
    }
