#!/usr/bin/env python3
"""settings 语义核须区分 sampling 开关与 pool 配置。"""

import copy
from typing import Optional

from core.modules.strategy.launcher.run_service import StrategyFingerprintManager
from core.modules.strategy.services.cache.simulator_res_db_cache.config import derive_run_mode
from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
    to_settings_hash,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_resolver import (
    semantic_core,
)


def _example_canonical(*, use_sampling: bool, pool_file: Optional[str] = None) -> dict:
    import importlib

    mod = importlib.import_module("userspace.strategies.example.settings")
    raw = copy.deepcopy(dict(mod.settings))
    raw.setdefault("sampling", {})
    raw["sampling"]["use_sampling"] = use_sampling
    if pool_file is not None:
        raw["sampling"].setdefault("pool", {})
        raw["sampling"]["pool"]["file"] = pool_file
    return StrategyFingerprintManager.canonicalize_settings(raw)


def test_semantic_core_keeps_sampling_when_use_sampling_false():
    core = semantic_core(_example_canonical(use_sampling=False))
    assert "sampling" in core
    assert core["sampling"].get("use_sampling") is False


def test_settings_hash_differs_on_use_sampling_toggle():
    h_off = to_settings_hash(semantic_core(_example_canonical(use_sampling=False)))
    h_on = to_settings_hash(semantic_core(_example_canonical(use_sampling=True)))
    assert h_off != h_on


def test_settings_hash_differs_on_pool_while_sampling_off():
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


def test_derive_run_mode_follows_use_sampling():
    off = _example_canonical(use_sampling=False)
    on = _example_canonical(use_sampling=True)
    assert derive_run_mode(off) == "full"
    assert derive_run_mode(on) == "sampling"
