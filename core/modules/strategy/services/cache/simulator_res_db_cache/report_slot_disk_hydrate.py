"""工作台 ``result_report`` 槽位：DB 仅存轻量摘要 + 磁盘相对路径，按需从产物目录合并正文。

- **enum**：``enumMetrics`` 等大字段落在 ``0_report_enum.json``；表内可只保留 ``enumerator_output_dir`` 等 + ``enum_report_rel_path``。
- **capital_allocation**：逐股 ``stock_summary`` 与完整指标落在 ``summary_strategy.json``；表内可剥离并保留 ``capital_sim_version_dir`` + ``capital_full_summary_rel_path``。

读路径（lookup / BFF / 切片）在缺字段时尝试按路径合并，兼容旧行（仍内嵌完整 JSON）。"""
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
    """落库前：若枚举产物目录已有 ``0_report_enum.json``，则从槽位移除 ``enumMetrics``，只保留路径引用。"""
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
    """读取后：无 ``enumMetrics`` 时尝试从 ``0_report_enum.json`` 合并。"""
    if not isinstance(slot, dict) or not slot:
        return slot
    if slot.get("enumMetrics"):
        return slot
    vdir = str(slot.get("enumerator_output_dir") or slot.get("version_dir") or "").strip()
    if not vdir:
        return slot
    rel = str(slot.get("enum_report_rel_path") or _ENUM_REPORT_FILE).strip() or _ENUM_REPORT_FILE
    path = PathManager.strategy_simulation_enum(str(strategy_name).strip()) / vdir / rel
    disk = _read_json(path)
    if not disk:
        return slot
    merged = dict(disk)
    merged.update(slot)
    return merged


def compact_capital_slot_for_cache(
    strategy_name: str,
    slot: Dict[str, Any],
    *,
    capital_sim_version_dir: str,
) -> Dict[str, Any]:
    """落库前：若 ``summary_strategy.json`` 已写入本次模拟目录，则移除 ``stock_summary`` 等大块，只保留路径引用。"""
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
    """读取后：无 ``stock_summary``（或其它明显缺项）时尝试从 ``summary_strategy.json`` 合并。"""
    if not isinstance(slot, dict) or not slot:
        return slot
    if slot.get("stock_summary"):
        return slot
    vd = str(slot.get("capital_sim_version_dir") or "").strip()
    if not vd:
        return slot
    rel = str(slot.get("capital_full_summary_rel_path") or _CAPITAL_SUMMARY_FILE).strip() or _CAPITAL_SUMMARY_FILE
    path = PathManager.strategy_simulation_capital(str(strategy_name).strip()) / vd / rel
    disk = _read_json(path)
    if not disk:
        return slot
    merged = dict(disk)
    merged.update(slot)
    return merged


def hydrate_workbench_result_report(strategy_name: str, result_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """对整份 ``result_report`` 做 enum / capital 磁盘补全（幂等；旧数据已内嵌字段则不变）。"""
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
