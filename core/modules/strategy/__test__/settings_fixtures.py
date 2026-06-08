#!/usr/bin/env python3
"""最小可过 StrategySettings.validate 的 settings 片段（测试用）。"""

from __future__ import annotations

from typing import Any, Dict


def minimal_strategy_raw(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "is_enabled": True,
        "meta": {
            "display_name": "Test Strategy",
            "description": "test",
        },
        "core": {},
        "market_profile": "china_a_stock",
        "data": {
            "base_required_data": {"params": {"term": "daily", "adjust": "qfq"}},
            "min_required_records": 30,
        },
        "simulation": {"template": "standard"},
        "goal": {
            "expiration": {"fixed_window_in_days": 30, "is_trading_days": True},
            "stop_loss": {
                "stages": [{"name": "loss", "ratio": -0.2, "close_invest": True}],
            },
            "take_profit": {
                "stages": [{"name": "win", "ratio": 0.2, "sell_ratio": 0.5}],
            },
        },
    }
    for key, value in overrides.items():
        if key == "meta" and isinstance(value, dict):
            merged = dict(base.get("meta") or {})
            merged.update(value)
            base["meta"] = merged
        else:
            base[key] = value
    return base


__all__ = ["minimal_strategy_raw"]
