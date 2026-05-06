"""工作台列表与表单选项：策略分页、版本下拉（V2-02/03）、静态枚举（V2-04）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_manager import DataManager
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import DiscoveredStrategy
from core.modules.strategy.engines.shared.data_classes.strategy_settings.sampling_settings import (
    KNOWN_STRATEGIES,
)
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.settings import (
    _VALID_MODES,
)
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper

# 与 ``API.md`` V2-03：固定至多 10 条，不分页。
DROPDOWN_LIMIT = 10


def _summary(ds: DiscoveredStrategy) -> Dict[str, Any]:
    return {
        "name": ds.name,
        "is_enabled": bool(ds.is_enabled),
        "worker_class_name": ds.worker_class_name,
        "folder": str(ds.folder),
    }


def fetch_discovered_strategies_page(page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    """
    分页返回 userspace 发现到的策略摘要；``page`` 为 1-based，按 ``name`` 排序。
    """
    discovered = StrategyDiscoveryHelper.discover_strategies()
    ordered = sorted(discovered.values(), key=lambda d: d.name)
    total = len(ordered)
    if total == 0:
        return [], 0
    page = max(1, int(page))
    limit = max(1, int(limit))
    start = (page - 1) * limit
    chunk = ordered[start : start + limit]
    return [_summary(ds) for ds in chunk], total


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat(sep=" ", timespec="seconds")
    return str(dt)


def fetch_strategy_versions_dropdown(strategy_name: str) -> List[Dict[str, Any]]:
    """
    某策略工作台快照版本（最多 ``DROPDOWN_LIMIT`` 条，从新到旧）；无表或无行时 ``[]``。
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


# --- V2-04 静态选项（与校验层合法取值一致） ---

_CAPITAL_LABELS: Dict[str, str] = {
    "equal_capital": "等额资金",
    "equal_shares": "等额股数",
    "kelly": "Kelly",
    "custom": "自定义",
}

_SAMPLING_LABELS: Dict[str, str] = {
    "uniform": "均匀采样",
    "stratified": "分层采样",
    "random": "随机采样",
    "continuous": "连续采样",
    "pool": "股票池",
    "blacklist": "黑名单",
}


def items_capital_allocation_strategies() -> List[Dict[str, Any]]:
    """``capital_simulator.allocation.mode`` 可选值。"""
    ordered = ("equal_capital", "equal_shares", "kelly", "custom")
    modes = [m for m in ordered if m in _VALID_MODES]
    rest = sorted(m for m in _VALID_MODES if m not in modes)
    out: List[Dict[str, Any]] = []
    for m in modes + rest:
        label = _CAPITAL_LABELS.get(m, m)
        out.append({"value": m, "label": label})
    return out


def items_sampling_strategies() -> List[Dict[str, Any]]:
    """根级 ``sampling.strategy`` 可选值。"""
    ordered = ("continuous", "uniform", "stratified", "random", "pool", "blacklist")
    keys = [k for k in ordered if k in KNOWN_STRATEGIES]
    rest = sorted(k for k in KNOWN_STRATEGIES if k not in keys)
    out: List[Dict[str, Any]] = []
    for k in keys + rest:
        out.append({"value": k, "label": _SAMPLING_LABELS.get(k, k)})
    return out
