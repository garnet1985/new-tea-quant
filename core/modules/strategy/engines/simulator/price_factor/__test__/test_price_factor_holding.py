#!/usr/bin/env python3
import unittest
from unittest.mock import patch

from core.modules.market_profile import clear_market_profile_cache, get_market_profile
from core.modules.strategy.engines.simulator.price_factor.data_classes.investment import (
    PriceFactorInvestment,
)
from core.modules.strategy.engines.simulator.price_factor.helpers.holding import (
    position_fully_closed,
    remaining_position_ratio,
    resolve_holding_until,
)
from core.modules.strategy.engines.shared.data_classes.investment_state import (
    InvestmentLifecycle,
    InvestmentOutcome,
)
from core.modules.strategy.engines.simulator.price_factor.worker import PriceFactorWorker


class TestPriceFactorHoldingHelpers(unittest.TestCase):
    def test_remaining_position_ratio_ladder(self):
        self.assertAlmostEqual(
            remaining_position_ratio([{"sell_ratio": 0.5}, {"sell_ratio": 1.0}]),
            0.0,
        )
        self.assertAlmostEqual(remaining_position_ratio([{"sell_ratio": 0.5}]), 0.5)
        self.assertEqual(remaining_position_ratio([]), 1.0)

    def test_resolve_holding_until_open_blocks_to_backtest_end(self):
        self.assertEqual(
            resolve_holding_until(
                processed_targets=[],
                buy_date="20250408",
                backtest_end_date="20260101",
            ),
            "20260101",
        )

    def test_resolve_holding_until_closed_uses_last_exit(self):
        targets = [
            {"date": "20240227", "sell_ratio": 1.0},
        ]
        self.assertEqual(
            resolve_holding_until(
                processed_targets=targets,
                buy_date="20240205",
                backtest_end_date="20260101",
            ),
            "20240227",
        )


class TestPriceFactorInvestmentOpen(unittest.TestCase):
    def test_open_when_all_sells_skipped(self):
        inv = PriceFactorInvestment.from_opportunity(
            {
                "opportunity_id": "18",
                "buy_date": "20250408",
                "buy_price": 1.71,
                "sell_date": "20250620",
                "status": "loss",
                "roi": -0.87,
            },
            [],
            backtest_end_date="20260101",
        )
        self.assertEqual(inv.lifecycle, InvestmentLifecycle.OPEN.value)
        self.assertIsNone(inv.outcome)
        self.assertIsNone(inv.sell_date)
        self.assertEqual(inv.completed_targets, [])
        self.assertEqual(inv.roi, 0.0)
        self.assertEqual(inv.profit, 0.0)

    def test_closed_from_executed_targets_not_enum(self):
        inv = PriceFactorInvestment.from_opportunity(
            {
                "opportunity_id": "1",
                "buy_date": "20240122",
                "buy_price": 10.0,
                "sell_date": "20240202",
                "status": "loss",
                "roi": -0.2,
            },
            [
                {
                    "date": "20240202",
                    "sell_ratio": 1.0,
                    "weighted_profit": -2.0,
                    "reason": "loss10%",
                },
            ],
            backtest_end_date="20260101",
        )
        self.assertEqual(inv.lifecycle, InvestmentLifecycle.COMPLETE.value)
        self.assertEqual(inv.outcome, InvestmentOutcome.LOSS.value)
        self.assertEqual(inv.sell_date, "20240202")
        self.assertAlmostEqual(inv.roi, -0.2)


class TestPriceFactorWorkerHoldingMutex(unittest.TestCase):
    def setUp(self):
        clear_market_profile_cache()

    def tearDown(self):
        clear_market_profile_cache()

    def _run_worker(self, opportunities, targets, targets_index):
        profile = get_market_profile("china_a_stock")
        _, limit_down = profile.compute_limit_prices("000584.SZ", 1.0)
        payload = {
            "stock_id": "000584.SZ",
            "strategy_name": "demo",
            "opportunities_path": "/tmp/opp",
            "targets_path": "/tmp/tgt",
            "output_version_dir": "/tmp/out",
            "market_profile_id": "china_a_stock",
            "config": {
                "start_date": "20250101",
                "end_date": "20260101",
                "simulation": {
                    "edges": {"allow_buy_at_limit_up": False, "allow_sell_at_limit_down": False},
                },
            },
            "_bench_skip_save": True,
        }
        worker = PriceFactorWorker(payload)
        def _hook_side_effect(name, *args, **_kwargs):
            if name == "on_price_factor_after_process_stock":
                return None
            return args[0] if args else None

        with patch.object(worker.hooks_dispatcher, "call_hook", side_effect=_hook_side_effect):
            with patch(
                "core.modules.strategy.engines.simulator.price_factor.worker.StrategyOutputReaderService"
            ) as reader_cls:
                reader_cls.return_value.load_rows_for_stock.return_value = (
                    opportunities,
                    targets,
                    targets_index,
                )
                with patch(
                    "core.modules.strategy.engines.simulator.price_factor.worker.load_stock_klines",
                    return_value=[],
                ):
                    return worker._simulate()

    def test_skipped_limit_down_sell_blocks_subsequent_buy(self):
        """000584 场景：跌停止损被跳过后，不得再开新仓。"""
        opportunities = [
            {
                "opportunity_id": "18",
                "trigger_date": "20250407",
                "buy_date": "20250408",
                "buy_price": 1.71,
                "sell_date": "20250620",
                "status": "loss",
                "roi": -0.87,
            },
            {
                "opportunity_id": "23",
                "trigger_date": "20250620",
                "buy_date": "20250623",
                "buy_price": 0.22,
                "sell_date": "20250710",
                "status": "win",
                "roi": 0.47,
            },
        ]
        targets = [
            {
                "opportunity_id": "18",
                "date": "20250620",
                "sell_price": 0.22,
                "sell_ratio": 1.0,
                "weighted_profit": -1.49,
                "reason": "loss10%",
                "sell_at_limit_down": True,
                "sell_prev_close": 1.0,
            },
            {
                "opportunity_id": "23",
                "date": "20250710",
                "sell_price": 0.29,
                "sell_ratio": 1.0,
                "weighted_profit": 0.07,
                "reason": "win20%",
                "sell_at_limit_down": False,
                "sell_prev_close": 0.28,
            },
        ]
        targets_index = {"18": [0], "23": [1]}
        summary = self._run_worker(opportunities, targets, targets_index)
        investments = summary["investments"]
        self.assertEqual(len(investments), 1)
        self.assertEqual(investments[0]["opportunity_id"], "18")
        self.assertEqual(investments[0]["lifecycle"], InvestmentLifecycle.OPEN.value)
        self.assertEqual(investments[0]["completed_targets"], [])
        self.assertIsNotNone(investments[0].get("pending_exit"))
        self.assertEqual(summary["skipped_sell_at_limit_down"], 1)

    def test_closed_position_allows_next_buy_after_exit(self):
        opportunities = [
            {
                "opportunity_id": "1",
                "buy_date": "20240102",
                "buy_price": 10.0,
                "sell_date": "20240110",
                "status": "win",
                "roi": 0.1,
            },
            {
                "opportunity_id": "2",
                "buy_date": "20240115",
                "buy_price": 11.0,
                "sell_date": "20240120",
                "status": "win",
                "roi": 0.05,
            },
        ]
        targets = [
            {
                "opportunity_id": "1",
                "date": "20240110",
                "sell_price": 11.0,
                "sell_ratio": 1.0,
                "weighted_profit": 1.0,
                "reason": "win10%",
                "sell_at_limit_down": False,
                "sell_prev_close": 10.5,
            },
            {
                "opportunity_id": "2",
                "date": "20240120",
                "sell_price": 11.5,
                "sell_ratio": 1.0,
                "weighted_profit": 0.5,
                "reason": "win10%",
                "sell_at_limit_down": False,
                "sell_prev_close": 11.2,
            },
        ]
        targets_index = {"1": [0], "2": [1]}
        summary = self._run_worker(opportunities, targets, targets_index)
        self.assertEqual(len(summary["investments"]), 2)

    def test_partial_exit_keeps_position_open(self):
        opportunities = [
            {
                "opportunity_id": "1",
                "buy_date": "20240102",
                "buy_price": 10.0,
                "sell_date": "20240120",
                "status": "win",
                "roi": 0.1,
            },
            {
                "opportunity_id": "2",
                "buy_date": "20240125",
                "buy_price": 11.0,
                "sell_date": "20240201",
                "status": "win",
                "roi": 0.05,
            },
        ]
        targets = [
            {
                "opportunity_id": "1",
                "date": "20240110",
                "sell_price": 11.0,
                "sell_ratio": 0.5,
                "weighted_profit": 0.5,
                "reason": "win10%",
                "sell_at_limit_down": False,
                "sell_prev_close": 10.5,
            },
            {
                "opportunity_id": "1",
                "date": "20240120",
                "sell_price": 9.0,
                "sell_ratio": 1.0,
                "weighted_profit": -1.0,
                "reason": "loss10%",
                "sell_at_limit_down": True,
                "sell_prev_close": 10.0,
            },
            {
                "opportunity_id": "2",
                "date": "20240201",
                "sell_price": 11.5,
                "sell_ratio": 1.0,
                "weighted_profit": 0.5,
                "reason": "win10%",
                "sell_at_limit_down": False,
                "sell_prev_close": 11.2,
            },
        ]
        targets_index = {"1": [0, 1], "2": [2]}
        summary = self._run_worker(opportunities, targets, targets_index)
        investments = summary["investments"]
        self.assertEqual(len(investments), 1)
        self.assertEqual(investments[0]["lifecycle"], InvestmentLifecycle.OPEN.value)
        self.assertEqual(len(investments[0]["completed_targets"]), 1)
        self.assertFalse(position_fully_closed(investments[0]["completed_targets"]))


if __name__ == "__main__":
    unittest.main()
