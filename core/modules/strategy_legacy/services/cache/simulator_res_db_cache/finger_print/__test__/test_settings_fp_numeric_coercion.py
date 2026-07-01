"""UI int vs CLI float 须产出相同 settings_fp。"""
from __future__ import annotations

import copy

from core.modules.strategy.__test__.settings_fixtures import minimal_strategy_raw
from core.modules.strategy.launcher.run_service import StrategyFingerprintManager
from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
    to_settings_hash,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_resolver import (
    semantic_core,
)


def _canonical_base_settings() -> dict:
    raw = minimal_strategy_raw(
        fees={
            "commission_rate": 0.00025,
            "min_commission": 5.0,
            "stamp_duty_rate": 0.001,
            "transfer_fee_rate": 0.0,
        },
        simulation={
            "template": "custom",
            "monitor_price_model": "close",
            "buy_price_model": "next_open",
            "sell_price_model": "close",
            "slippage": {"buy_bps": 5.0, "sell_bps": 5.0},
        },
    )
    return StrategyFingerprintManager.canonicalize_settings(raw)


def test_settings_fp_matches_int_vs_float_fees_and_slippage():
    base = _canonical_base_settings()

    ui_like = copy.deepcopy(base)
    ui_like.setdefault("fees", {})
    ui_like["fees"]["min_commission"] = 5
    ui_like["fees"]["transfer_fee_rate"] = 0
    ui_like.setdefault("simulation", {}).setdefault("slippage", {})
    ui_like["simulation"]["slippage"]["buy_bps"] = 5
    ui_like["simulation"]["slippage"]["sell_bps"] = 5

    fp_cli = to_settings_hash(semantic_core(base))
    fp_ui = to_settings_hash(semantic_core(ui_like))
    assert fp_cli == fp_ui


def test_min_required_records_accepts_ui_float():
    """工作台 number 字段常为 JSON float，不得被 apply_defaults 重置为 100。"""
    raw = minimal_strategy_raw()
    raw.setdefault("data", {})["min_required_records"] = 30.0
    normalized = StrategyFingerprintManager.canonicalize_settings(raw)
    assert normalized["data"]["min_required_records"] == 30.0
