"""GlobalEntityCache.seed_system_globals 无 IO 主线。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.modules.backtest_engine.core.shared.owned_shared_memory import (
    shared_memory_available,
)
from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)

pytestmark = pytest.mark.force_run


def test_seed_system_globals_filters_blank_ids() -> None:
    cache = GlobalEntityCache(settings=MagicMock())
    cache.seed_system_globals(
        stock_list=["000001.SZ", "", "  ", "000002.SZ"],
        latest_completed_trading_date="20240110",
    )
    assert cache.get_stock_ids() == ["000001.SZ", "000002.SZ"]
    assert cache._global_meta["latest_completed_trading_date"] == "20240110"


def test_shared_memory_readable_after_create() -> None:
    if not shared_memory_available():
        pytest.skip("shared_memory 不可用")
    cache = GlobalEntityCache(settings=MagicMock())
    cache._global_data = {"k": [1, 2, 3]}
    cache._create_shared_memory()
    try:
        info = cache.get_shm_info()
        assert info["shm_name"]
        assert info["shm_size"] > 0
        assert GlobalEntityCache.access_shared_memory(
            info["shm_name"], info["shm_size"]
        ) == {"k": [1, 2, 3]}
        assert GlobalEntityCache.access_shared_memory(
            info["shm_name"], info["shm_size"]
        ) == {"k": [1, 2, 3]}
    finally:
        cache.cleanup()
    assert cache.get_shm_info()["shm_name"] == ""
