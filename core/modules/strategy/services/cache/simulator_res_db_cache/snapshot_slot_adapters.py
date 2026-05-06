#!/usr/bin/env python3
"""
``result_report`` 按 simulator 槽位的读/写适配；枚举写入前的摘要整形亦在本模块。

保持 ``cache_service.SimulatorResDbCacheService`` 仅负责表操作。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.enums import Simulator

from .cache_service import SimulatorResDbCacheService


def sanitize_enum_payload_for_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """浅拷贝并去掉值为 ``None`` 的顶层键，便于 JSON 落库。"""
    raw = dict(payload or {})
    return {k: v for k, v in raw.items() if v is not None}


def lookup_enum_cache(
    strategy_name: str,
    settings_finger_print_id: str,
    env_fingerprint_id: str,
) -> Optional[Tuple[List[Dict[str, Any]], int]]:
    """双指纹命中且 ``result_report.enum`` 为非空 dict 时返回 ``([payload], snapshot_id)``；否则 ``None``。"""
    svc = SimulatorResDbCacheService()
    row = svc.load_cache_by_fingerprints(
        str(strategy_name),
        str(settings_finger_print_id or "").strip(),
        str(env_fingerprint_id or "").strip(),
    )
    if not row:
        return None
    snapshot_id = int((row or {}).get("snapshot_id") or 0)
    rr = dict((row or {}).get("result_report") or {})
    enum_raw = rr.get("enum")
    if not isinstance(enum_raw, dict) or not enum_raw:
        return None
    return ([enum_raw], snapshot_id)


def persist_enum_snapshot(
    strategy_name: str,
    *,
    settings_snapshot_api: Dict[str, Any],
    report_enum: Dict[str, Any],
    settings_fingerprint_id: str,
    env_fingerprint_id: str,
) -> int:
    """写入或合并 ``enum`` 槽位。"""
    return SimulatorResDbCacheService().set_cache(
        strategy_name=str(strategy_name),
        settings_snapshot=dict(settings_snapshot_api or {}),
        simulator=Simulator.ENUMERATOR,
        simulator_report=dict(report_enum or {}),
        settings_fingerprint_id=str(settings_fingerprint_id or "").strip(),
        env_fingerprint_id=str(env_fingerprint_id or "").strip(),
    )


def lookup_price_factor_cache(
    strategy_name: str,
    settings_finger_print_id: str,
    env_fingerprint_id: str,
) -> Optional[Tuple[Dict[str, Any], int]]:
    """双指纹命中且 ``result_report.price_factor`` 为非空 dict 时返回 ``(payload, snapshot_id)``。"""
    svc = SimulatorResDbCacheService()
    row = svc.load_cache_by_fingerprints(
        str(strategy_name),
        str(settings_finger_print_id or "").strip(),
        str(env_fingerprint_id or "").strip(),
    )
    if not row:
        return None
    snapshot_id = int((row or {}).get("snapshot_id") or 0)
    rr = dict((row or {}).get("result_report") or {})
    slot = rr.get("price_factor")
    if not isinstance(slot, dict) or not slot:
        return None
    return (slot, snapshot_id)


def persist_price_factor_snapshot(
    strategy_name: str,
    *,
    settings_snapshot_api: Dict[str, Any],
    report_price_factor: Dict[str, Any],
    settings_fingerprint_id: str,
    env_fingerprint_id: str,
) -> int:
    """写入或合并 ``price_factor`` 槽位。"""
    return SimulatorResDbCacheService().set_cache(
        strategy_name=str(strategy_name),
        settings_snapshot=dict(settings_snapshot_api or {}),
        simulator=Simulator.PRICE_FACTOR,
        simulator_report=dict(report_price_factor or {}),
        settings_fingerprint_id=str(settings_fingerprint_id or "").strip(),
        env_fingerprint_id=str(env_fingerprint_id or "").strip(),
    )


def lookup_capital_allocation_cache(
    strategy_name: str,
    settings_finger_print_id: str,
    env_fingerprint_id: str,
) -> Optional[Tuple[Dict[str, Any], int]]:
    """双指纹命中且 ``result_report.capital_allocation`` 为非空 dict 时返回 ``(payload, snapshot_id)``。"""
    svc = SimulatorResDbCacheService()
    row = svc.load_cache_by_fingerprints(
        str(strategy_name),
        str(settings_finger_print_id or "").strip(),
        str(env_fingerprint_id or "").strip(),
    )
    if not row:
        return None
    snapshot_id = int((row or {}).get("snapshot_id") or 0)
    rr = dict((row or {}).get("result_report") or {})
    slot = rr.get("capital_allocation")
    if not isinstance(slot, dict) or not slot:
        return None
    return (slot, snapshot_id)


def persist_capital_allocation_snapshot(
    strategy_name: str,
    *,
    settings_snapshot_api: Dict[str, Any],
    report_capital_allocation: Dict[str, Any],
    settings_fingerprint_id: str,
    env_fingerprint_id: str,
) -> int:
    """写入或合并 ``capital_allocation`` 槽位。"""
    return SimulatorResDbCacheService().set_cache(
        strategy_name=str(strategy_name),
        settings_snapshot=dict(settings_snapshot_api or {}),
        simulator=Simulator.CAPITAL_ALLOCATION,
        simulator_report=dict(report_capital_allocation or {}),
        settings_fingerprint_id=str(settings_fingerprint_id or "").strip(),
        env_fingerprint_id=str(env_fingerprint_id or "").strip(),
    )


__all__ = [
    "lookup_capital_allocation_cache",
    "lookup_enum_cache",
    "lookup_price_factor_cache",
    "persist_capital_allocation_snapshot",
    "persist_enum_snapshot",
    "persist_price_factor_snapshot",
    "sanitize_enum_payload_for_snapshot",
]
