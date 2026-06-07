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
    vdir = str(base.get("enumerator_output_dir") or "").strip()
    if not vdir:
        return base
    report_path = PathManager.strategy_simulation_enum(str(strategy_name).strip()) / vdir / _ENUM_REPORT_FILE
    if not report_path.is_file():
        return base
    out = dict(base)
    out.pop("enumMetrics", None)
    out["enum_report_rel_path"] = _ENUM_REPORT_FILE
    return _strip_none_values(out)


def enum_opportunity_count_from_slot(slot: Optional[Dict[str, Any]]) -> Optional[int]:
    """从 enum 槽位或 hydrate 后的 ``enumMetrics`` 解析机会总数（执行面板 ``opportunities``）。"""
    if not isinstance(slot, dict) or not slot:
        return None
    for key in ("opportunities", "total_opportunities"):
        if key in slot and slot.get(key) is not None:
            try:
                return int(slot[key])
            except (TypeError, ValueError):
                pass
    em = slot.get("enumMetrics")
    if isinstance(em, dict) and em.get("totalOpportunities") is not None:
        try:
            return int(em["totalOpportunities"])
        except (TypeError, ValueError):
            return None
    return None


def attach_enum_opportunities_field(slot: Dict[str, Any]) -> Dict[str, Any]:
    """为执行面板 / progress 切片补齐顶层 ``opportunities``（与 ``enumMetrics`` 同源）。"""
    if not isinstance(slot, dict) or not slot:
        return slot
    out = dict(slot)
    count = enum_opportunity_count_from_slot(out)
    if count is not None:
        out["opportunities"] = count
    return out


def hydrate_enum_slot(strategy_name: str, slot: Dict[str, Any]) -> Dict[str, Any]:
    """有 ``enumerator_output_dir`` 且磁盘报告存在时，以 ``0_report_enum.json`` 为正文，叠加路径元数据。"""
    if not isinstance(slot, dict) or not slot:
        return slot
    sn = str(strategy_name or "").strip()
    vdir = str(slot.get("enumerator_output_dir") or "").strip()
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
    if not isinstance(out.get("backtest_period"), dict):
        meta = _read_json(PathManager.strategy_simulation_enum(sn) / vdir / "0_metadata.json")
        if isinstance(meta, dict):
            bp = meta.get("backtest_period")
            if isinstance(bp, dict) and bp.get("start_date") and bp.get("end_date"):
                out["backtest_period"] = dict(bp)
            elif meta.get("start_date") and meta.get("end_date"):
                out["backtest_period"] = {
                    "start_date": str(meta.get("start_date") or "").strip(),
                    "end_date": str(meta.get("end_date") or "").strip(),
                    "start_source": "",
                    "end_source": "",
                }
    return out


def _metadata_refs_enum_output_dir(meta: Dict[str, Any]) -> str:
    """从 capital ``0_metadata.json`` 解析其依赖的枚举产物目录名。"""
    if not isinstance(meta, dict):
        return ""
    ov = meta.get("output_version")
    if isinstance(ov, dict):
        return str(ov.get("enumerator_output_dir") or "").strip()
    return ""


def _metadata_refs_price_output_dir(meta: Dict[str, Any]) -> str:
    """从 capital ``0_metadata.json`` 解析其依赖的 price 产物目录名。"""
    if not isinstance(meta, dict):
        return ""
    ov = meta.get("output_version")
    if isinstance(ov, dict):
        ref = str(ov.get("output_version_dir") or "").strip()
        if ref:
            return ref
    elif isinstance(ov, str):
        ref = str(ov).strip()
        if ref:
            return ref
    run = meta.get("output_version_run")
    if isinstance(run, dict):
        ref = str(run.get("output_version_dir") or run.get("price_output_version_dir") or "").strip()
        if ref:
            return ref
    return ""


def _resolve_capital_output_dir(
    strategy_name: str,
    *,
    match: Any,
) -> Optional[str]:
    sn = str(strategy_name or "").strip()
    needle = str(match or "").strip()
    if not (sn and needle):
        return None
    root = PathManager.strategy_simulation_capital(sn)
    if not root.is_dir():
        return None
    best_name = ""
    best_id = -1
    for child in root.iterdir():
        if not child.is_dir() or not child.name.isdigit():
            continue
        meta = _read_json(child / "0_metadata.json")
        if not meta:
            continue
        if not (
            _metadata_refs_enum_output_dir(meta) == needle
            or _metadata_refs_price_output_dir(meta) == needle
        ):
            continue
        summary = child / _CAPITAL_SUMMARY_FILE
        if not summary.is_file():
            continue
        try:
            vid = int(child.name)
        except ValueError:
            continue
        if vid > best_id:
            best_id = vid
            best_name = child.name
    return best_name or None


def resolve_capital_output_dir_for_enum_run(
    strategy_name: str,
    enum_output_dir: str,
) -> Optional[str]:
    """按枚举 ``enumerator_output_dir`` 查找最新 capital 产物目录。"""
    return _resolve_capital_output_dir(strategy_name, match=enum_output_dir)


def resolve_capital_output_dir_for_price_run(
    strategy_name: str,
    price_output_dir: str,
) -> Optional[str]:
    """按 price ``output_version_run.output_version_dir`` 查找最新 capital 产物目录。"""
    return _resolve_capital_output_dir(strategy_name, match=price_output_dir)


def compact_capital_slot_for_cache(
    strategy_name: str,
    slot: Dict[str, Any],
    *,
    capital_output_version_dir: str,
) -> Dict[str, Any]:
    """落库前：``summary_strategy.json`` 已存在时移除 ``stock_summary`` 等大块，只保留路径引用。"""
    out = _strip_none_values(dict(slot or {}))
    vd = str(capital_output_version_dir or "").strip()
    if not vd:
        return out
    summary_path = (
        PathManager.strategy_simulation_capital(str(strategy_name).strip()) / vd / _CAPITAL_SUMMARY_FILE
    )
    if not summary_path.is_file():
        return out
    out.pop("stock_summary", None)
    out["capital_output_version_dir"] = vd
    out["capital_full_summary_rel_path"] = _CAPITAL_SUMMARY_FILE
    return _strip_none_values(out)


def hydrate_capital_slot(strategy_name: str, slot: Dict[str, Any]) -> Dict[str, Any]:
    """有 ``capital_output_version_dir`` 且 ``summary_strategy.json`` 存在时，以磁盘摘要为正文，叠加路径元数据。"""
    if not isinstance(slot, dict) or not slot:
        return slot
    sn = str(strategy_name or "").strip()
    vd = str(slot.get("capital_output_version_dir") or "").strip()
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
        rr["enum"] = attach_enum_opportunities_field(hydrate_enum_slot(sn, en))
    cap = rr.get("capital_allocation")
    if isinstance(cap, dict) and cap:
        rr["capital_allocation"] = hydrate_capital_slot(sn, cap)
    return rr


__all__ = [
    "attach_enum_opportunities_field",
    "compact_capital_slot_for_cache",
    "compact_enum_slot_for_cache",
    "enum_opportunity_count_from_slot",
    "hydrate_capital_slot",
    "hydrate_enum_slot",
    "hydrate_workbench_result_report",
    "resolve_capital_output_dir_for_enum_run",
    "resolve_capital_output_dir_for_price_run",
]
