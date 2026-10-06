"""按 ``opportunity_selection`` 重排当日可买机会。

只排序，不占槽、不算仓位。已持仓不参与归一化。
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Set, Tuple

from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    OpportunitySelectionRule,
)


class OpportunityRanker:
    """当日机会排序。``mode`` 为 ``order`` 或 ``weight``。"""

    @classmethod
    def order(
        cls,
        available: Sequence[Opportunity],
        rules: Sequence[OpportunitySelectionRule],
        *,
        mode: str,
        base_data_key: str,
        held_entity_ids: Optional[Set[str]] = None,
    ) -> List[Opportunity]:
        held = {
            str(item or "").strip()
            for item in (held_entity_ids or set())
            if str(item or "").strip()
        }
        eligible = [
            opp
            for opp in available
            if not _is_held(opp, held)
        ]
        if not eligible or not rules:
            return eligible
        if mode == "order":
            return sorted(eligible, key=lambda opp: _order_key(opp, rules, base_data_key))
        if mode == "weight":
            scores = _weight_scores(eligible, rules, base_data_key)
            indexed = list(enumerate(eligible))
            indexed.sort(key=lambda pair: (-scores[pair[0]], pair[0]))
            return [opp for _, opp in indexed]
        return eligible


def _is_held(opportunity: Opportunity, held: Set[str]) -> bool:
    entity_id = str(getattr(opportunity, "stock_id", "") or "").strip()
    return bool(entity_id) and entity_id in held


def _snapshot_number(
    opportunity: Opportunity,
    rule: OpportunitySelectionRule,
    base_data_key: str,
) -> Optional[float]:
    snapshot = opportunity.signal_snapshot
    if not isinstance(snapshot, dict):
        return None
    raw = snapshot.get(rule.snapshot_key(base_data_key))
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    number = float(raw)
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _order_key(
    opportunity: Opportunity,
    rules: Sequence[OpportunitySelectionRule],
    base_data_key: str,
) -> Tuple[Tuple[bool, float], ...]:
    parts: List[Tuple[bool, float]] = []
    for rule in rules:
        number = _snapshot_number(opportunity, rule, base_data_key)
        missing = number is None
        magnitude = 0.0 if missing else float(number)
        if rule.direction == "DESC":
            magnitude = -magnitude
        parts.append((missing, magnitude))
    return tuple(parts)


def _weight_scores(
    opportunities: Sequence[Opportunity],
    rules: Sequence[OpportunitySelectionRule],
    base_data_key: str,
) -> List[float]:
    weight_total = sum(abs(float(rule.weight)) for rule in rules)
    if weight_total <= 0:
        return [0.0 for _ in opportunities]
    columns = [
        _normalized_column(opportunities, rule, base_data_key) for rule in rules
    ]
    scores: List[float] = []
    for index in range(len(opportunities)):
        score = 0.0
        for rule, column in zip(rules, columns):
            share = float(rule.weight) / weight_total
            score += share * column[index]
        scores.append(score)
    return scores


def _normalized_column(
    opportunities: Sequence[Opportunity],
    rule: OpportunitySelectionRule,
    base_data_key: str,
) -> List[float]:
    present: Dict[int, float] = {}
    for index, opportunity in enumerate(opportunities):
        number = _snapshot_number(opportunity, rule, base_data_key)
        if number is not None:
            present[index] = number
    if len(present) < 2:
        return [0.0 for _ in opportunities]
    low = min(present.values())
    high = max(present.values())
    if high == low:
        return [0.0 for _ in opportunities]
    span = high - low
    return [
        (present[index] - low) / span if index in present else 0.0
        for index in range(len(opportunities))
    ]
