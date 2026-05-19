#!/usr/bin/env python3
"""枚举报告：涨跌停标注汇总。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Union

from core.modules.strategy.engines.shared.helpers.tradability import (
    row_buy_at_limit_up,
    row_sell_at_limit_down,
)

_COUNT_KEYS = (
    "buy_tradability_sample_count",
    "buy_at_limit_up_count",
    "sell_tradability_sample_count",
    "sell_at_limit_down_count",
)


def _empty_counts() -> Dict[str, int]:
    return {k: 0 for k in _COUNT_KEYS}


def merge_tradability_counts(*parts: Dict[str, int]) -> Dict[str, int]:
    out = _empty_counts()
    for part in parts:
        if not isinstance(part, dict):
            continue
        for k in _COUNT_KEYS:
            out[k] += int(part.get(k) or 0)
    return out


def tradability_ratios(counts: Dict[str, int]) -> Dict[str, float]:
    buy_sample = int(counts.get("buy_tradability_sample_count") or 0)
    buy_limit = int(counts.get("buy_at_limit_up_count") or 0)
    sell_sample = int(counts.get("sell_tradability_sample_count") or 0)
    sell_limit = int(counts.get("sell_at_limit_down_count") or 0)
    return {
        "limit_up_buy_ratio": round((buy_limit / buy_sample) * 100.0, 1) if buy_sample else 0.0,
        "limit_down_sell_ratio": round((sell_limit / sell_sample) * 100.0, 1) if sell_sample else 0.0,
    }


def tradability_bundle_from_opportunities(
    opportunities: List[Dict[str, Any]],
) -> Dict[str, Union[int, float]]:
    counts = count_tradability_in_opportunities(opportunities)
    return {**counts, **tradability_ratios(counts)}


def count_tradability_in_opportunities(opportunities: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = _empty_counts()
    for opp in opportunities:
        if not isinstance(opp, dict):
            continue
        try:
            has_buy = float(opp.get("buy_price") or 0.0) > 0 and str(opp.get("buy_date") or "").strip()
        except (TypeError, ValueError):
            has_buy = False
        if has_buy:
            flagged = row_buy_at_limit_up(opp)
            if flagged is not None:
                counts["buy_tradability_sample_count"] += 1
                if flagged:
                    counts["buy_at_limit_up_count"] += 1
        for target in _iter_targets(opp.get("completed_targets")):
            flagged = row_sell_at_limit_down(target)
            if flagged is not None:
                counts["sell_tradability_sample_count"] += 1
                if flagged:
                    counts["sell_at_limit_down_count"] += 1
    return counts


def collect_target_tradability_from_dir(output_dir: Path) -> Dict[str, int]:
    counts = _empty_counts()
    if not output_dir.is_dir():
        return {
            "sell_tradability_sample_count": 0,
            "sell_at_limit_down_count": 0,
        }
    for entry in output_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith("_targets.csv"):
            continue
        try:
            with entry.open("r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    flagged = row_sell_at_limit_down(row)
                    if flagged is None:
                        continue
                    counts["sell_tradability_sample_count"] += 1
                    if flagged:
                        counts["sell_at_limit_down_count"] += 1
        except OSError:
            continue
    return {
        "sell_tradability_sample_count": counts["sell_tradability_sample_count"],
        "sell_at_limit_down_count": counts["sell_at_limit_down_count"],
    }


def _iter_targets(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, str) and raw.strip():
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    return [t for t in raw if isinstance(t, dict)]


__all__ = [
    "collect_target_tradability_from_dir",
    "count_tradability_in_opportunities",
    "merge_tradability_counts",
    "tradability_bundle_from_opportunities",
    "tradability_ratios",
]
