"""ScanCacheManager 单元测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.engines.scanner.helpers.cache_manager import (
    ScanCacheManager,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    StockInfo,
)

pytestmark = pytest.mark.force_run


def test_save_load_and_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "core.modules.strategy.core.engines.scanner.helpers.cache_manager.ProjectContext.path.get_strategy_scan_results_directory",
        lambda _name: tmp_path / "scan",
    )
    cache = ScanCacheManager("demo_strategy", max_cache_days=2)
    opp = Opportunity(
        stock=StockInfo(id="600000.SH", name="浦发"),
        record_of_today={"date": "20240110", "close": 10.0},
        trigger_date="20240110",
        trigger_price=10.0,
    )
    cache.save_opportunities("20240110", [opp])
    loaded = cache.load_opportunities("20240110")
    assert len(loaded) == 1
    assert loaded[0].stock_id == "600000.SH"
    assert loaded[0].trigger_price == pytest.approx(10.0)

    cache.save_opportunities("20240111", [])
    assert not cache.opportunities_csv_path("20240111").is_file()

    for day in ("20240108", "20240109", "20240110"):
        (cache.cache_base_dir / day).mkdir(parents=True, exist_ok=True)
        (cache.cache_base_dir / day / "opportunities.csv").write_text(
            "x\n", encoding="utf-8"
        )
    cache.cleanup_old_cache()
    remaining = sorted(d.name for d in cache.cache_base_dir.iterdir() if d.is_dir())
    assert remaining == ["20240109", "20240110"]
