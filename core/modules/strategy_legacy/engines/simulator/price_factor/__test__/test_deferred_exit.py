#!/usr/bin/env python3
"""顺延退出重试单元测试。"""

import unittest
from unittest.mock import patch

from core.modules.market_profile import clear_market_profile_cache, get_market_profile
from core.modules.strategy.engines.shared.data_classes.investment_state import (
    InvestmentLifecycle,
    InvestmentOutcome,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.investment import (
    PriceFactorInvestment,
)
from core.modules.strategy.engines.simulator.price_factor.helpers.deferred_exit import (
    retry_deferred_exits,
)
from core.modules.strategy.engines.simulator.price_factor.worker import PriceFactorWorker


class TestDeferredExitRetry(unittest.TestCase):
    def setUp(self):
        clear_market_profile_cache()

    def tearDown(self):
        clear_market_profile_cache()

    def test_retry_succeeds_after_limit_down_gap(self):
        sim = StrategySimulationSettings.from_strategy_root(
            {"simulation": {"template": "standard"}}
        )
        profile = get_market_profile("china_a_stock")
        skipped = [
            {
                "opportunity_id": "18",
                "date": "20250620",
                "sell_price": 0.22,
                "sell_ratio": 1.0,
                "reason": "loss10%",
                "sell_at_limit_down": True,
            },
        ]
        klines = [
            {"date": "20250620", "open": 0.22, "close": 0.22, "high": 0.22, "low": 0.22},
            {"date": "20250623", "open": 0.25, "close": 0.25, "high": 0.26, "low": 0.24},
        ]
        processed, pending, skips = retry_deferred_exits(
            buy_price=1.71,
            processed_targets=[],
            skipped_targets=skipped,
            klines=klines,
            sim_settings=sim,
            market_profile=profile,
            stock_id="000584.SZ",
            allow_sell_at_limit=False,
        )
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]["date"], "20250623")
        self.assertIsNone(pending)
        self.assertEqual(skips, 0)

    def test_worker_completes_after_deferred_exit(self):
        opportunities = [
            {
                "opportunity_id": "18",
                "trigger_date": "20250407",
                "buy_date": "20250408",
                "buy_price": 1.71,
                "sell_date": "20250620",
                "roi": -0.87,
            },
            {
                "opportunity_id": "23",
                "trigger_date": "20250620",
                "buy_date": "20250623",
                "buy_price": 0.22,
                "sell_date": "20250710",
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
        klines = [
            {"date": "20250620", "open": 0.22, "close": 0.22, "high": 0.22, "low": 0.22},
            {"date": "20250623", "open": 0.25, "close": 0.25, "high": 0.26, "low": 0.24},
            {"date": "20250710", "open": 0.29, "close": 0.29, "high": 0.30, "low": 0.28},
        ]
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

        def _hook_side_effect(name, ctx, **_kwargs):
            if name == "on_price_factor_after_process_stock":
                return None
            pf = getattr(ctx, "price_factor", None)
            if pf is None:
                return None
            if name == "on_price_factor_opportunity_trigger":
                return pf.opportunity_row
            if name == "on_price_factor_target_hit":
                return pf.target_row
            return None

        with patch.object(worker.hooks_dispatcher, "call_hook", side_effect=_hook_side_effect):
            with patch(
                "core.modules.strategy.engines.simulator.price_factor.worker.StrategyOutputReaderService"
            ) as reader_cls:
                reader_cls.return_value.load_rows_for_stock.return_value = (
                    opportunities,
                    targets,
                    {"18": [0], "23": [1]},
                )
                with patch(
                    "core.modules.strategy.engines.simulator.price_factor.worker.load_stock_klines",
                    return_value=klines,
                ):
                    summary = worker._simulate()

        investments = summary["investments"]
        self.assertEqual(len(investments), 1)
        inv = investments[0]
        self.assertEqual(inv["opportunity_id"], "18")
        self.assertEqual(inv["lifecycle"], InvestmentLifecycle.COMPLETE.value)
        self.assertEqual(inv["outcome"], InvestmentOutcome.LOSS.value)
        self.assertEqual(len(inv["completed_targets"]), 1)
        self.assertEqual(inv["completed_targets"][0]["sell_date"], "20250623")


if __name__ == "__main__":
    unittest.main()
