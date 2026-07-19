"""模拟结果缓存管理器（Facade 编排层查写 ``sys_strategy_workbench_snapshot``）。"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

from core.modules.strategy.contracts import SimulateKind
from core.modules.strategy.core.services.simulation_cache.base_cache_manager import (
    BaseCacheManager,
)
from core.modules.strategy.core.services.simulation_cache.fingerprints import (
    FingerprintResult,
)

logger = logging.getLogger(__name__)


class _ReportSlot(str, Enum):
    """工作台 ``result_report`` 内槽位名。"""

    ENUM = "enum"
    PRICE_FACTOR = "price_factor"
    CAPITAL_ALLOCATION = "capital_allocation"


_KIND_TO_SLOT = {
    SimulateKind.ENUMERATE: _ReportSlot.ENUM,
    SimulateKind.PRICE_FACTOR: _ReportSlot.PRICE_FACTOR,
    SimulateKind.CAPITAL_ALLOCATION: _ReportSlot.CAPITAL_ALLOCATION,
}

# Facade / Pipeline 结果 key → DB slot（含历史别名 ``enum``）
_VALUE_KEY_TO_SLOT = {
    SimulateKind.ENUMERATE.value: _ReportSlot.ENUM,
    _ReportSlot.ENUM.value: _ReportSlot.ENUM,
    SimulateKind.PRICE_FACTOR.value: _ReportSlot.PRICE_FACTOR,
    SimulateKind.CAPITAL_ALLOCATION.value: _ReportSlot.CAPITAL_ALLOCATION,
}

_SLOT_TO_KIND_VALUE = {
    _ReportSlot.ENUM: SimulateKind.ENUMERATE.value,
    _ReportSlot.PRICE_FACTOR: SimulateKind.PRICE_FACTOR.value,
    _ReportSlot.CAPITAL_ALLOCATION: SimulateKind.CAPITAL_ALLOCATION.value,
}


def _kind_to_slot(kind: Union[SimulateKind, str, None]) -> Optional[_ReportSlot]:
    if kind is None:
        return _ReportSlot.ENUM
    if isinstance(kind, SimulateKind):
        return _KIND_TO_SLOT.get(kind)
    text = str(kind).strip().lower()
    if text in _VALUE_KEY_TO_SLOT:
        return _VALUE_KEY_TO_SLOT[text]
    try:
        return _KIND_TO_SLOT.get(SimulateKind(text))
    except ValueError:
        return None


def _value_key_to_slot(key: str) -> Optional[_ReportSlot]:
    return _VALUE_KEY_TO_SLOT.get(str(key or "").strip().lower())


def _slot_to_kind_value(slot: _ReportSlot) -> str:
    return _SLOT_TO_KIND_VALUE.get(slot) or slot.value


class SimulationCacheManager(BaseCacheManager):
    """模拟三步缓存（enum / price_factor / capital_allocation 槽位）。

    边界:
    - 负责: 双指纹 AND 查/写工作台快照；按 kind 读写槽位
    - 不负责: 算指纹、跑 Pipeline
    - 调用方: Strategy.simulate
    """

    table_name: ClassVar[str] = "sys_strategy_workbench_snapshot"
    max_rows: ClassVar[int] = 50

    @classmethod
    def get_cache(
        cls,
        key: str,
        fps: FingerprintResult,
        kind: Any = None,
    ) -> Optional[Dict[str, Any]]:
        """按 strategy + settings_fp + env_fp 取行；目标 kind 槽位非空则命中。

        返回形状与 ``Strategy._run_steps`` 一致：``{kind.value: slot_payload}``。
        """
        strategy_name = str(key or "").strip()
        slot = _kind_to_slot(kind if kind is not None else SimulateKind.ENUMERATE)
        if not strategy_name or slot is None:
            return None
        sfp = str(fps.settings_fp or "").strip()
        efp = str(fps.env_fp or "").strip()
        if not sfp or not efp:
            return None

        row = cls._load_row_by_fingerprints(strategy_name, sfp, efp)
        if not row:
            return None
        reports = cls._reports_from_row(row)
        payload = reports.get(slot.value)
        if not isinstance(payload, dict) or not payload:
            return None
        return {_slot_to_kind_value(slot): dict(payload)}

    @classmethod
    def set_cache(
        cls,
        key: str,
        fps: FingerprintResult,
        value: Dict[str, Any],
    ) -> int:
        """把 ``value`` 内各 step 结果 merge 进双指纹对应行；返回 workbench version（失败 0）。

        ``value`` 形如 ``{"enumerate": {...}, "price_factor": {...}}``（也可直接用 DB slot 名）。
        写入 ``enum`` 时清除下游 ``price_factor`` / ``capital_allocation``。
        """
        strategy_name = str(key or "").strip()
        sfp = str(fps.settings_fp or "").strip()
        efp = str(fps.env_fp or "").strip()
        if not strategy_name or not sfp or not efp:
            return 0

        slots = cls._extract_slots(value)
        if not slots:
            return 0

        model = cls._table()
        if model is None:
            logger.warning("表 %s 未注册，跳过 set_cache", cls.table_name)
            return 0

        row = cls._load_row_by_fingerprints(strategy_name, sfp, efp, model=model)
        if row:
            version = int(row.get("version") or 0)
            if version <= 0:
                return 0
            merged = cls._reports_from_row(row)
            merged = cls._merge_slots(merged, slots)
            merged = cls._bump_write_count(merged)
            model.update_result_report(
                strategy_name,
                version,
                merged,
                settings_finger_print_id=sfp,
                env_fingerprint_id=efp,
            )
            cls._prune_oldest(model, strategy_name)
            return version

        merged = cls._merge_slots({}, slots)
        merged = cls._attach_initial_write_meta(merged)
        created = model.create_snapshot(
            strategy_name,
            dict(fps.settings_diff or {}),
            merged,
            settings_finger_print_id=sfp,
            env_fingerprint_id=efp,
        )
        version = int((created or {}).get("version") or 0)
        if version > 0:
            cls._prune_oldest(model, strategy_name)
        return version

    @classmethod
    def find_enum_output_version(
        cls,
        key: str,
        fps: FingerprintResult,
    ) -> Optional[str]:
        """双指纹命中且 enum 槽有 ``version_id`` 时返回之（供补跑 price/capital 用）。"""
        cached = cls.get_cache(key, fps, SimulateKind.ENUMERATE)
        if not cached:
            return None
        slot = cached.get(SimulateKind.ENUMERATE.value) or {}
        version_id = slot.get("version_id")
        if version_id is None or str(version_id).strip() == "":
            return None
        return str(version_id)

    # --- simulation-specific ----------------------------------------------

    @classmethod
    def _extract_slots(
        cls,
        value: Dict[str, Any],
    ) -> List[Tuple[_ReportSlot, Dict[str, Any]]]:
        out: List[Tuple[_ReportSlot, Dict[str, Any]]] = []
        for key, payload in (value or {}).items():
            if str(key).startswith("_"):
                continue
            slot = _value_key_to_slot(str(key))
            if slot is None or not isinstance(payload, dict) or not payload:
                continue
            cleaned = {k: v for k, v in payload.items() if v is not None}
            if cleaned:
                out.append((slot, cleaned))
        out.sort(key=lambda item: 0 if item[0] is _ReportSlot.ENUM else 1)
        return out

    @classmethod
    def _merge_slots(
        cls,
        existing: Dict[str, Any],
        slots: List[Tuple[_ReportSlot, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        merged = dict(existing or {})
        for slot, payload in slots:
            merged[slot.value] = dict(payload)
            if slot is _ReportSlot.ENUM:
                merged.pop(_ReportSlot.PRICE_FACTOR.value, None)
                merged.pop(_ReportSlot.CAPITAL_ALLOCATION.value, None)
        return merged


__all__ = ["SimulationCacheManager"]
