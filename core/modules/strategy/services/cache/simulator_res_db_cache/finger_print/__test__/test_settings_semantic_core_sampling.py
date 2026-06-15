#!/usr/bin/env python3
"""settings 语义核须区分 sampling 开关与 pool 配置。"""
from __future__ import annotations

import copy
from typing import Optional

from core.modules.strategy.__test__.settings_fixtures import minimal_strategy_raw
from core.modules.strategy.launcher.run_service import StrategyFingerprintManager
from core.modules.strategy.services.cache.simulator_res_db_cache.config import derive_run_mode
from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
    to_settings_hash,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_resolver import (
    semantic_core,
)

_EXAMPLE_RAW = minimal_strategy_raw(
    sampling={
        "use_sampling": False,
        "strategy": "uniform",
        "sampling_amount": 1000,
    },
)


def _example_canonical(*, use_sampling: bool, pool_file: Optional[str] = None) -> dict:
    raw = copy.deepcopy(_EXAMPLE_RAW)
    raw.setdefault("sampling", {})
    raw["sampling"]["use_sampling"] = use_sampling
    if pool_file is not None:
        raw["sampling"].setdefault("pool", {})
        raw["sampling"]["pool"]["file"] = pool_file
    return StrategyFingerprintManager.canonicalize_settings(raw)


def test_semantic_core_and_run_mode_follow_sampling_toggle():
    off = _example_canonical(use_sampling=False)
    on = _example_canonical(use_sampling=True)

    core_off = semantic_core(off)
    assert "sampling" in core_off
    assert core_off["sampling"].get("use_sampling") is False

    assert derive_run_mode(off) == "full"
    assert derive_run_mode(on) == "sampling"
    assert to_settings_hash(core_off) != to_settings_hash(semantic_core(on))


def test_settings_hash_differs_on_pool_when_sampling_off():
    h_a = to_settings_hash(
        semantic_core(
            _example_canonical(use_sampling=False, pool_file="stock_lists/a.txt")
        )
    )
    h_b = to_settings_hash(
        semantic_core(
            _example_canonical(use_sampling=False, pool_file="stock_lists/b.txt")
        )
    )
    assert h_a != h_b
