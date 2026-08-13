"""GlobalEntityCache.seed_system_globals 无 IO 主线。"""
from __future__ import annotations

from unittest.mock import MagicMock

from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)

pytestmark = __import__("pytest").mark.force_run


def test_seed_system_globals_filters_blank_ids() -> None:
    cache = GlobalEntityCache(settings=MagicMock())
    cache.seed_system_globals(
        stock_list=["000001.SZ", "", "  ", "000002.SZ"],
        latest_completed_trading_date="20240110",
    )
    assert cache.get_stock_ids() == ["000001.SZ", "000002.SZ"]
    assert cache._global_meta["latest_completed_trading_date"] == "20240110"
