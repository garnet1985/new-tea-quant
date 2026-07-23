"""Shared PIT / bar helpers for enumerator timeline hooks (entity + slice)."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.core.engines.enumerator.shared.performance_tracker.performance_tracker import (
    EnumJobPerfRecorder,
)

logger = logging.getLogger(__name__)


class PitBars:
    """Contract.until → per-entity PIT，以及当日 base bar 判定。

    边界:
    - 负责: until 聚合、bar_on 校验、ready_date（until 前门闩）
    - 不负责: 日循环、Investment
    - 调用方: entity / slice TimelineHooks
    """

    @staticmethod
    def ready_date_by_entity(
        base_contract: Any,
        entity_ids: Sequence[str],
        *,
        min_required: int,
        time_field: str = "date",
    ) -> Dict[str, str]:
        """各 entity 最早可做事日 = 第 min_required 根 K 线日期；不足则空串。

        用于 until 之前短路：as_of < ready_date 时不应 scan / 不应为「做事」付 until。
        """
        need = max(1, int(min_required or 1))
        out: Dict[str, str] = {}
        if base_contract is None:
            return {str(eid).strip(): "" for eid in entity_ids if str(eid).strip()}
        for raw_id in entity_ids:
            entity_id = str(raw_id or "").strip()
            if not entity_id:
                continue
            rows = base_contract.get_entity_data(entity_id) if hasattr(
                base_contract, "get_entity_data"
            ) else None
            if not isinstance(rows, list) or len(rows) < need:
                out[entity_id] = ""
                continue
            out[entity_id] = str(rows[need - 1].get(time_field) or "").strip()
        return out

    @staticmethod
    def job_min_ready_date(ready_by_entity: Dict[str, str]) -> str:
        """job 内最早可做事日；全无 ready 则返回空串。"""
        dates = [str(d).strip() for d in (ready_by_entity or {}).values() if str(d).strip()]
        return min(dates) if dates else ""

    @staticmethod
    def load_pit_by_entity(
        entity_contracts: Dict[str, Any],
        as_of: str,
        *,
        perf: Optional[EnumJobPerfRecorder] = None,
    ) -> Dict[str, Dict[str, Any]]:
        pit_data_by_entity: Dict[str, Dict[str, Any]] = {}
        for data_key, contract in entity_contracts.items():
            try:
                until_t0 = time.perf_counter()
                pit_data_dict = contract.until(as_of=as_of)
                if perf is not None:
                    perf.record_contract_until(
                        str(data_key),
                        time.perf_counter() - until_t0,
                    )
            except Exception as exc:
                logger.error(
                    "Contract.until 失败：data_key=%s as_of=%s error=%s",
                    data_key,
                    as_of,
                    exc,
                    exc_info=True,
                )
                continue
            for entity_id, pit_rows in pit_data_dict.items():
                pit_data_by_entity.setdefault(entity_id, {})[data_key] = pit_rows
        return pit_data_by_entity

    @staticmethod
    def bar_on(
        per_entity_pit: Dict[str, Any],
        *,
        base_data_key: str,
        as_of: str,
        min_required: int,
    ) -> Optional[Dict[str, Any]]:
        base_rows = per_entity_pit.get(base_data_key)
        if not isinstance(base_rows, list) or not base_rows:
            return None
        last = base_rows[-1]
        if str(last.get("date") or "") != as_of:
            return None
        if len(base_rows) < min_required:
            return None
        for key in ("open", "high", "low", "close"):
            if key not in last:
                raise ValueError(f"K 线缺少字段 {key!r}: date={as_of}")
        return last


__all__ = ["PitBars"]
