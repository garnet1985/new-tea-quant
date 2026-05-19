"""工作台 ``result_report`` 槽位：DB 存轻量摘要 + 磁盘路径，读取时以产物 JSON 为正文。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.infra.project_context.path_manager import PathManager

logger = logging.getLogger(__name__)

_ENUM_REPORT_FILE = "0_report_enum.json"
_CAPITAL_SUMMARY_FILE = "summary_strategy.json"


def _strip_none_values(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw = dict(payload or {})
    return {k: v for k, v in raw.items() if v is not None}


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("failed to read json %s", path, exc_info=True)
        return None


def compact_enum_slot_for_cache(strategy_name: str, slot: Dict[str, Any]) -> Dict[str, Any]:
    """落库前：产物目录已有 ``0_report_enum.json`` 时移除 ``enumMetrics``，只保留路径引用。"""
    base = _strip_none_values(dict(slot or {}))
    vdir = str(base.get("enumerator_output_dir") or base.get("version_dir") or "").strip()
    if not vdir:
        return base
    report_path = PathManager.strategy_simulation_enum(str(strategy_name).strip()) / vdir / _ENUM_REPORT_FILE
    if not report_path.is_file():
        return base
    out = dict(base)
    out.pop("enumMetrics", None)
    out["enum_report_rel_path"] = _ENUM_REPORT_FILE
    return _strip_none_values(out)


def hydrate_enum_slot(strategy_name: str, slot: Dict[str, Any]) -> Dict[str, Any]:
    """有 ``enumerator_output_dir`` 且磁盘报告存在时，以 ``0_report_enum.json`` 为正文，叠加路径元数据。"""
    if not isinstance(slot, dict) or not slot:
        return slot
    sn = str(strategy_name or "").strip()
    vdir = str(slot.get("enumerator_output_dir") or slot.get("version_dir") or "").strip()
    if not (vdir and sn):
        return slot
    rel = str(slot.get("enum_report_rel_path") or _ENUM_REPORT_FILE).strip() or _ENUM_REPORT_FILE
    path = PathManager.strategy_simulation_enum(sn) / vdir / rel
    disk = _read_json(path)
    if not disk:
        return slot
    out = dict(disk)
    for key, value in slot.items():
        if key != "enumMetrics":
            out[key] = value
    return out


def compact_capital_slot_for_cache(
    strategy_name: str,
    slot: Dict[str, Any],
    *,
    capital_sim_version_dir: str,
) -> Dict[str, Any]:
    """落库前：``summary_strategy.json`` 已存在时移除 ``stock_summary`` 等大块，只保留路径引用。"""
    out = _strip_none_values(dict(slot or {}))
    vd = str(capital_sim_version_dir or "").strip()
    if not vd:
        return out
    summary_path = (
        PathManager.strategy_simulation_capital(str(strategy_name).strip()) / vd / _CAPITAL_SUMMARY_FILE
    )
    if not summary_path.is_file():
        return out
    out.pop("stock_summary", None)
    out["capital_sim_version_dir"] = vd
    out["capital_full_summary_rel_path"] = _CAPITAL_SUMMARY_FILE
    return _strip_none_values(out)


def hydrate_capital_slot(strategy_name: str, slot: Dict[str, Any]) -> Dict[str, Any]:
    """有 ``capital_sim_version_dir`` 且 ``summary_strategy.json`` 存在时，以磁盘摘要为正文，叠加路径元数据。"""
    if not isinstance(slot, dict) or not slot:
        return slot
    sn = str(strategy_name or "").strip()
    vd = str(slot.get("capital_sim_version_dir") or "").strip()
    if not (vd and sn):
        return slot
    rel = str(slot.get("capital_full_summary_rel_path") or _CAPITAL_SUMMARY_FILE).strip() or _CAPITAL_SUMMARY_FILE
    path = PathManager.strategy_simulation_capital(sn) / vd / rel
    disk = _read_json(path)
    if not disk:
        return slot
    out = dict(disk)
    for key, value in slot.items():
        if key != "stock_summary":
            out[key] = value
    return out


def hydrate_workbench_result_report(strategy_name: str, result_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """对整份 ``result_report`` 做 enum / capital 磁盘补全（幂等）。"""
    rr = dict(result_report or {})
    sn = str(strategy_name or "").strip()
    if not sn:
        return rr
    en = rr.get("enum")
    if isinstance(en, dict) and en:
        rr["enum"] = hydrate_enum_slot(sn, en)
    cap = rr.get("capital_allocation")
    if isinstance(cap, dict) and cap:
        rr["capital_allocation"] = hydrate_capital_slot(sn, cap)
    return rr


__all__ = [
    "compact_capital_slot_for_cache",
    "compact_enum_slot_for_cache",
    "hydrate_capital_slot",
    "hydrate_enum_slot",
    "hydrate_workbench_result_report",
]
