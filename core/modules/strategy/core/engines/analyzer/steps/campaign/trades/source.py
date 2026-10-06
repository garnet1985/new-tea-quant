"""从价格层回测产物读实体投资明细（战役 trades 用）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResultsManager,
)
from core.modules.strategy.core.services.artifacts import (
    PRICE_INVESTMENTS_SUFFIX,
    ArtifactStore,
    EnumerateStore,
    GoalAchievementRow,
    PriceFactorStore,
    PriceInvestmentRow,
)


class PriceSource:
    """读 price_factor 产物 → ``{"entities": [...]}``，带 enum capture 联表。"""

    def __init__(self, store: ArtifactStore) -> None:
        if not isinstance(store, PriceFactorStore):
            raise TypeError("PriceSource requires PriceFactorStore")
        self.store = store
        self._runtime_raw = store.read_json("runtime_env")

    @classmethod
    def load(cls, store: ArtifactStore) -> Dict[str, Any]:
        return cls(store).build()

    def build(self) -> Dict[str, Any]:
        enum_store = self._open_upstream_enum_store()
        return {"entities": self._collect_entities(self.store, enum_store)}

    def _collect_entities(
        self,
        store: PriceFactorStore,
        enum_store: Optional[EnumerateStore],
    ) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        for entity_id in store.entity_ids or _price_entity_ids(store):
            rows_raw = store.investments(entity_id)
            if not rows_raw:
                continue
            snapshots = _enum_capture_index(enum_store, entity_id)
            goal_index = _goal_index(store.goals(entity_id))
            rows = [
                _join_price_investment(
                    row,
                    capture=snapshots.get(row.opportunity_id, {}),
                    completed_goals=goal_index.get(row.opportunity_id, []),
                )
                for row in rows_raw
            ]
            entities.append({"entity_id": entity_id, "investments": rows})
        return entities

    def _open_upstream_enum_store(self) -> Optional[EnumerateStore]:
        raw = self._runtime_raw if isinstance(self._runtime_raw, dict) else {}
        enum_dir = str(raw.get("enum_output_dir") or "").strip()
        enum_version_id = str(raw.get("enum_version_id") or "").strip()
        if enum_dir:
            path = Path(enum_dir)
            if path.is_dir():
                return EnumerateStore.open(
                    path,
                    version_id=enum_version_id or path.name,
                )
        return None


def _price_entity_ids(store: PriceFactorStore) -> List[str]:
    nested = store._scan_suffix(store.entities_dir(), PRICE_INVESTMENTS_SUFFIX)
    if nested:
        return nested
    return store._scan_suffix(store.output_dir, PRICE_INVESTMENTS_SUFFIX)


def _enum_capture_index(
    enum_store: Optional[EnumerateStore], entity_id: str
) -> Dict[str, Dict[str, Any]]:
    if enum_store is None:
        return {}
    eid = str(entity_id or "").strip()
    if not eid:
        return {}
    return {
        str(row.investment_id or "").strip(): dict(row.signal_snapshot or {})
        for row in EnumResultsManager.at(enum_store.output_dir).results(eid)
        if str(row.investment_id or "").strip()
    }


def _goal_index(rows: Sequence[GoalAchievementRow]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        inv_id = str(row.investment_id or "").strip()
        if not inv_id:
            continue
        out.setdefault(inv_id, []).append(
            {
                "goal_name": row.goal_name,
                "date": row.date,
                "price": row.price,
                "price_hfq": row.price_hfq,
                "exit_ratio": row.exit_ratio,
                "profit": row.profit,
                "weighted_profit": row.weighted_profit,
                "reason": row.reason,
                "roi": row.roi,
            }
        )
    return out


def _join_price_investment(
    row: PriceInvestmentRow,
    *,
    capture: Dict[str, Any],
    completed_goals: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "investment_id": row.opportunity_id,
        "engine": {
            "enter_date": row.enter_date,
            "enter_price": row.enter_price,
            "enter_price_hfq": row.enter_price_hfq,
            "exit_date": row.exit_date,
            "exit_price": row.exit_price,
            "exit_price_hfq": row.exit_price_hfq,
            "exit_reason": row.exit_reason,
            "skip_reason": row.skip_reason,
            "lifecycle": row.lifecycle,
            "result": row.result,
            "roi": row.roi,
            "holding_days": row.holding_days,
            "holding_trading_days": row.holding_trading_days,
        },
        "completed_goals": list(completed_goals),
        "capture": dict(capture),
    }
