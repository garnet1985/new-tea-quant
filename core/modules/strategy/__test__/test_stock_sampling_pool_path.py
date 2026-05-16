#!/usr/bin/env python3
"""股票池文件路径须使用策略目录名（example），而非 settings.name 展示名。"""

from core.modules.strategy.engines.shared.helpers.stock_sampling import StockSamplingHelper


class TestStockSamplingPoolPath:
    def test_load_pool_file_under_strategy_folder(self):
        ids = StockSamplingHelper._load_stock_ids_from_file(
            strategy_name="example",
            relative_file_path="stock_lists/test_stocks.txt",
            field_name="test",
        )
        assert "000001.SZ" in ids
        assert len(ids) >= 10

    def test_wrong_folder_name_returns_empty(self):
        ids = StockSamplingHelper._load_stock_ids_from_file(
            strategy_name="RSI超跌",
            relative_file_path="stock_lists/test_stocks.txt",
            field_name="test",
        )
        assert ids == []
