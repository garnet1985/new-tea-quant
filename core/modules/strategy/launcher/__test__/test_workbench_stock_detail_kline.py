#!/usr/bin/env python3
import unittest

from core.modules.strategy.launcher.workbench_stock_detail import (
    _api_candle_row,
    _load_candles_and_indicators,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.data_manager.data_manager import DataManager


class TestWorkbenchStockDetailKline(unittest.TestCase):
    def test_api_candle_row_only_ohlc_keys(self):
        row = {
            "date": "20230601",
            "open": 6.861,
            "close": 6.87,
            "high": 6.889,
            "low": 6.815,
            "id": "000019.SZ",
            "term": "daily",
            "volume": 100,
        }
        out = _api_candle_row(row)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(set(out.keys()), {"date", "open", "close", "high", "low"})
        self.assertEqual(out["open"], 6.86)

    def test_load_candles_and_indicators_qfq_shape(self):
        dm = DataManager()
        view = StrategySettingsView.from_dict({
            "data": {
                "base_required_data": {"params": {"term": "daily", "adjust": "qfq"}},
                "indicators": {"rsi": [{"length": 14}]},
            }
        })
        candles, series = _load_candles_and_indicators(
            stock_id="000019.SZ",
            settings_view=view,
            backtest_period={"start_date": "20230601", "end_date": "20230630"},
            data_manager=dm,
        )
        self.assertTrue(candles)
        self.assertEqual(set(candles[0].keys()), {"date", "open", "close", "high", "low"})
        self.assertTrue(series)


if __name__ == "__main__":
    unittest.main()
