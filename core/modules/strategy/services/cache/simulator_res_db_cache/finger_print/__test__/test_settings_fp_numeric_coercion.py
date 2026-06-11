"""UI int vs CLI float 须产出相同 settings_fp。"""
from __future__ import annotations

import copy

from core.modules.strategy.launcher.run_service import StrategyFingerprintManager
from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
    to_settings_hash,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_resolver import (
    semantic_core,
)
from core.modules.strategy.services.discovery.discovery import StrategyDiscoveryHelper
from core.infra.project_context.path_manager import PathManager


def test_settings_fp_matches_int_vs_float_fees_and_slippage():
    disc = StrategyDiscoveryHelper.load_strategy(PathManager.strategy("example"))
    assert disc is not None
    base = StrategyFingerprintManager.canonicalize_settings(dict(disc.settings.to_dict()))

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
