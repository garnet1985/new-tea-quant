#!/usr/bin/env python3
"""股票池文件路径须使用策略目录名（example），而非 settings.name 展示名。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.engines.shared.helpers.stock_sampling import StockSamplingHelper

_POOL_REL = "stock_lists/test_stocks.txt"
_POOL_CODES = [
    "000001.SZ",
    "000002.SZ",
    "000004.SZ",
    "000006.SZ",
    "000007.SZ",
    "000008.SZ",
    "000009.SZ",
    "000010.SZ",
    "000011.SZ",
    "000012.SZ",
]


@pytest.fixture
def strategy_userspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """userspace 在仓库外被 gitignore；测试内自建策略目录与股票池文件。"""
    example_dir = tmp_path / "example"
    pool_file = example_dir / _POOL_REL
    pool_file.parent.mkdir(parents=True, exist_ok=True)
    pool_file.write_text("\n".join(_POOL_CODES) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        "core.modules.strategy.engines.shared.helpers.stock_sampling.PathManager.strategy",
        lambda strategy_name: tmp_path / strategy_name,
    )
    return tmp_path


class TestStockSamplingPoolPath:
    def test_load_pool_file_under_strategy_folder(self, strategy_userspace_root: Path):
        ids = StockSamplingHelper._load_stock_ids_from_file(
            strategy_name="example",
            relative_file_path=_POOL_REL,
            field_name="test",
        )
        assert "000001.SZ" in ids
        assert len(ids) >= 10

    def test_wrong_folder_name_returns_empty(self, strategy_userspace_root: Path):
        ids = StockSamplingHelper._load_stock_ids_from_file(
            strategy_name="RSI超跌",
            relative_file_path=_POOL_REL,
            field_name="test",
        )
        assert ids == []
