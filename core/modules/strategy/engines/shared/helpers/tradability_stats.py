#!/usr/bin/env python3
"""枚举产物上的涨跌停标注统计。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from core.modules.strategy.engines.shared.helpers.market_profile_runtime import (
    row_buy_at_limit_up,
    row_sell_at_limit_down,
)


def count_tradability_in_opportunities(
    opportunities: List[Dict[str, Any]],
) -> Dict[str, int]:
    buy_sample = 0
    buy_limit_up = 0
    sell_sample = 0
    sell_limit_down = 0
    for opp in opportunities:
        if not isinstance(opp, dict):
            continue
        try:
            buy_price = float(opp.get("buy_price") or 0.0)
        except (TypeError, ValueError):
            buy_price = 0.0
        buy_date = str(opp.get("buy_date") or "").strip()
        if buy_price > 0 and buy_date:
            flagged = row_buy_at_limit_up(opp)
            if flagged is not None:
                buy_sample += 1
                if flagged:
                    buy_limit_up += 1
        targets = opp.get("completed_targets")
        if isinstance(targets, str) and targets.strip():
            try:
                targets = json.loads(targets)
            except json.JSONDecodeError:
                targets = []
        if not isinstance(targets, list):
            continue
        for target in targets:
            if not isinstance(target, dict):
                continue
            flagged = row_sell_at_limit_down(target)
            if flagged is not None:
                sell_sample += 1
                if flagged:
                    sell_limit_down += 1
    return {
        "buy_tradability_sample_count": buy_sample,
        "buy_at_limit_up_count": buy_limit_up,
        "sell_tradability_sample_count": sell_sample,
        "sell_at_limit_down_count": sell_limit_down,
    }


def count_tradability_in_target_rows(target_rows: List[Dict[str, Any]]) -> Dict[str, int]:
    sell_sample = 0
    sell_limit_down = 0
    for row in target_rows:
        if not isinstance(row, dict):
            continue
        flagged = row_sell_at_limit_down(row)
        if flagged is not None:
            sell_sample += 1
            if flagged:
                sell_limit_down += 1
    return {
        "sell_tradability_sample_count": sell_sample,
        "sell_at_limit_down_count": sell_limit_down,
    }


def collect_target_tradability_from_dir(output_dir: Path) -> Dict[str, int]:
    sell_sample = 0
    sell_limit_down = 0
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
                reader = csv.DictReader(f)
                partial = count_tradability_in_target_rows(list(reader))
        except OSError:
            continue
        sell_sample += int(partial.get("sell_tradability_sample_count") or 0)
        sell_limit_down += int(partial.get("sell_at_limit_down_count") or 0)
    return {
        "sell_tradability_sample_count": sell_sample,
        "sell_at_limit_down_count": sell_limit_down,
    }


def merge_tradability_counts(*parts: Dict[str, int]) -> Dict[str, int]:
    keys = (
        "buy_tradability_sample_count",
        "buy_at_limit_up_count",
        "sell_tradability_sample_count",
        "sell_at_limit_down_count",
    )
    out = {k: 0 for k in keys}
    for part in parts:
        if not isinstance(part, dict):
            continue
        for k in keys:
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


__all__ = [
    "collect_target_tradability_from_dir",
    "count_tradability_in_opportunities",
    "count_tradability_in_target_rows",
    "merge_tradability_counts",
    "tradability_ratios",
]
