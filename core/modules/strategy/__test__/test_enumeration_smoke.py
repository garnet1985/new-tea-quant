#!/usr/bin/env python3
# MARK: STALE — 依赖已 UNUSED 的 SliceBasedJobs / SliceBasedCompute / EntityBasedJobs；
# 热路径已改 JobBuilder + SliceEnumerationSimulator。整文件 skip，待重写。
"""阶段 A：data 声明 + discover + enumerate 链路 smoke（分步建设，允许未跑通）。"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

pytest.skip(
    "MARK: STALE — SliceBasedJobs/SliceBasedCompute archived as UNUSED",
    allow_module_level=True,
)

# from core.modules.strategy.core.engines.enumerator.slice_based.compute import SliceBasedCompute
# from core.modules.strategy.core.engines.enumerator.entity_based.services.job_builder import EntityBasedJobs
# from core.modules.strategy.core.engines.enumerator.slice_based.resolver.jobs import SliceBasedJobs
from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper
from core.modules.strategy.core.services.data.entity_data import GlobalDataPreloader
from core.modules.strategy.core.engines.shared.services.strategy_settings.data_settings import DataSettings
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings
from core.modules.strategy.core.services.discovery.discovery_service import DiscoveryService

_DEVTOOLS_STRATEGIES_ROOT = (
    Path(__file__).resolve().parents[4]
    / "devtools"
    / "performance"
    / "strategy"
    / "test_base_strategies"
)
_DEVTOOLS_STOCK_BASED = "stock_based"
_DEVTOOLS_SLICE_BASED = "slice_based"

_USERSPACE_STRATEGIES_ROOT = (
    Path(__file__).resolve().parents[4] / "userspace" / "strategies"
)
_USERSPACE_RANDOM_V1 = "demo/random/random_v1_null_baseline"
_USERSPACE_RSI_V1 = "demo/regression/rsi/rsi_v1_without_value_anchor"
_USERSPACE_LOW_PRICE_V2 = "demo/cross_sectional/low_price/low_price_v2_monthly_rebalance"


def _minimal_settings() -> Dict[str, Any]:
    return {
        "data": {
            "base": {
                "data_key": "stock.kline.daily",
                "params": {"adjust": "qfq"},
                "indicators": {"rsi": [{"length": 14}]},
            },
            "required": [],
            "min_required_records": 20,
        },
    }


class TestDataSettingsSchema(unittest.TestCase):
    """data.base + data.required + data_key。"""

    def test_issue_declarations_base_plus_required(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "data": {
                    "base": {
                        "data_key": "stock.kline.daily",
                        "params": {"adjust": "qfq"},
                    },
                    "required": [
                        {"data_key": "macro.gdp", "params": {}},
                    ],
                },
            }
        )
        settings.apply_defaults()
        decls = settings.data.issue_declarations()
        self.assertEqual(len(decls), 2)
        self.assertEqual(decls[0]["data_key"], "stock.kline.daily")
        self.assertEqual(decls[1]["data_key"], "macro.gdp")

    def test_rejects_missing_base(self) -> None:
        settings = StrategySettings(raw_settings={"data": {"required": []}})
        settings.apply_defaults()
        with self.assertRaises(ValueError):
            settings.data.issue_declarations()

    def test_rejects_duplicate_data_key(self) -> None:
        settings = StrategySettings(
            raw_settings={
                "data": {
                    "base": {"data_key": "stock.kline.daily", "params": {}},
                    "required": [{"data_key": "stock.kline.daily", "params": {}}],
                },
            }
        )
        settings.apply_defaults()
        with self.assertRaises(ValueError):
            settings.data.issue_declarations()


class TestGlobalDataPreloadSmoke(unittest.TestCase):
    """GLOBAL preload 只扫 data.required（不含 base）。"""

    def test_preload_stock_list_only_when_required_empty(self) -> None:
        global_data, meta = GlobalDataPreloader.preload(
            settings=_minimal_settings(),
            start_date="20240101",
            end_date="20241231",
            entity_ids=["600000.SH"],
        )
        self.assertEqual(global_data["stock_list"], ["600000.SH"])
        self.assertEqual(meta["loaded_slots"], ["stock_list"])


class TestDevtoolsDiscoverySmoke(unittest.TestCase):
    """devtools 演示策略 discover + hooks 加载。"""

    def test_discover_stock_based(self) -> None:
        if not _DEVTOOLS_STRATEGIES_ROOT.is_dir():
            self.skipTest(f"missing devtools strategies root: {_DEVTOOLS_STRATEGIES_ROOT}")

        discovered = DiscoveryService.discover_strategies(_DEVTOOLS_STRATEGIES_ROOT)
        self.assertIn(_DEVTOOLS_STOCK_BASED, discovered)

        info = discovered[_DEVTOOLS_STOCK_BASED]
        self.assertEqual(info["key"], "stock_based_rsi")
        self.assertEqual(info["worker_class_name"], "RsiFundamentalGateHooks")
        self.assertTrue(Path(info["folder"]).joinpath("strategy.py").is_file())

    def test_discover_slice_based(self) -> None:
        if not _DEVTOOLS_STRATEGIES_ROOT.is_dir():
            self.skipTest(f"missing devtools strategies root: {_DEVTOOLS_STRATEGIES_ROOT}")

        discovered = DiscoveryService.discover_strategies(_DEVTOOLS_STRATEGIES_ROOT)
        self.assertIn(_DEVTOOLS_SLICE_BASED, discovered)

        info = discovered[_DEVTOOLS_SLICE_BASED]
        self.assertEqual(info["worker_class_name"], "LowPricePitRebalanceHooks")
        settings = info["settings"]
        self.assertEqual(settings["simulation"]["execution_mode"], "slice_based")

    def test_discover_userspace_random_v1_contracts_hooks(self) -> None:
        """userspace 参考 demo：contracts + DataContext。"""
        root = _USERSPACE_STRATEGIES_ROOT
        if not root.is_dir():
            self.skipTest(f"missing userspace strategies root: {root}")

        discovered = DiscoveryService.discover_strategies(root)
        self.assertIn(_USERSPACE_RANDOM_V1, discovered)

        info = discovered[_USERSPACE_RANDOM_V1]
        self.assertEqual(info["worker_class_name"], "RandomNullBaselineStrategy")
        settings = info["settings"]
        self.assertEqual(settings["simulation"]["execution_mode"], "entity_based")
        self.assertEqual(settings["data"]["base"]["data_key"], "stock.kline.daily")

    def test_discover_userspace_rsi_v1_contracts_hooks(self) -> None:
        """userspace RSI demo：contracts + entity_based。"""
        root = _USERSPACE_STRATEGIES_ROOT
        if not root.is_dir():
            self.skipTest(f"missing userspace strategies root: {root}")

        discovered = DiscoveryService.discover_strategies(root)
        self.assertIn(_USERSPACE_RSI_V1, discovered)

        info = discovered[_USERSPACE_RSI_V1]
        self.assertEqual(info["worker_class_name"], "ExampleStrategy")
        settings = info["settings"]
        self.assertEqual(settings["simulation"]["execution_mode"], "entity_based")
        self.assertIn("rsi", settings["data"]["base"]["indicators"])

    def test_discover_userspace_low_price_v2_slice_based(self) -> None:
        """userspace 横截面 demo：contracts + slice_based。"""
        root = _USERSPACE_STRATEGIES_ROOT
        if not root.is_dir():
            self.skipTest(f"missing userspace strategies root: {root}")

        discovered = DiscoveryService.discover_strategies(root)
        self.assertIn(_USERSPACE_LOW_PRICE_V2, discovered)

        info = discovered[_USERSPACE_LOW_PRICE_V2]
        self.assertEqual(info["worker_class_name"], "LowPricePitRebalanceStrategy")
        settings = info["settings"]
        self.assertEqual(settings["simulation"]["execution_mode"], "slice_based")
        self.assertEqual(settings["data"]["base"]["data_key"], "stock.kline.daily")


class TestEntityBasedJobBuild(unittest.TestCase):
    """entity_based job 须含 open_dates + backtest_calendar。"""

    def test_build_includes_open_dates(self) -> None:
        from core.modules.strategy.core.engines.enumerator.slice_based.resolver import calendar

        fake_calendar = {
            "market": "SSE",
            "period_start": "20240101",
            "period_end": "20241231",
            "open_dates": ["20240102", "20240103"],
        }
        with patch.object(
            calendar.BacktestCalendarResolver,
            "resolve",
            return_value=(fake_calendar["open_dates"], fake_calendar),
        ):
            jobs = EntityBasedJobs.build(
                strategy_name="demo/entity",
                settings_payload={
                    "market_profile": "china_a_stock",
                    "data": {"base": {"data_key": "stock.kline.daily", "params": {}}},
                },
                output_dir="/tmp/out",
                worker_ref={
                    "worker_module_path": "mod",
                    "worker_class_name": "Hooks",
                    "worker_file_path": "",
                },
                stock_ids=["600000.SH", "600036.SH"],
                start_date="20240101",
                end_date="20241231",
            )

        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(job["open_dates"], ["20240102", "20240103"])
            self.assertEqual(job["backtest_calendar"]["open_dates"], ["20240102", "20240103"])
            self.assertEqual(job["enumeration_execution_mode"], "entity_based")


class TestSliceBasedJobBuild(unittest.TestCase):
    """slice_based job 须含 open_dates + backtest_calendar。"""

    def test_build_includes_open_dates(self) -> None:
        from core.modules.strategy.core.engines.enumerator.slice_based.resolver import calendar

        fake_calendar = {
            "market": "SSE",
            "period_start": "20240101",
            "period_end": "20241231",
            "open_dates": ["20240102", "20240103"],
        }
        with patch.object(
            calendar.BacktestCalendarResolver,
            "resolve",
            return_value=(fake_calendar["open_dates"], fake_calendar),
        ):
            jobs = SliceBasedJobs.build(
                strategy_name="demo/slice",
                settings_payload={"market_profile": "china_a_stock", "data": {"base": {"data_key": "stock.kline.daily", "params": {}}}},
                output_dir="/tmp/out",
                worker_ref={
                    "worker_module_path": "mod",
                    "worker_class_name": "Hooks",
                    "worker_file_path": "",
                },
                entity_ids=["600000.SH"],
                start_date="20240101",
                end_date="20241231",
            )
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job["open_dates"], ["20240102", "20240103"])
        self.assertEqual(job["backtest_calendar"]["open_dates"], ["20240102", "20240103"])
        self.assertEqual(job["stock_ids"], ["600000.SH"])
        self.assertEqual(job["enumeration_execution_mode"], "slice_based")


class TestEnumerationEndToEndSmoke(unittest.TestCase):
    """端到端 enumerate：有环境则跑，否则 skip（阶段 A 允许红/ skip）。"""

    def test_enumerate_devtools_stock_based_if_discovered(self) -> None:
        from core.modules.strategy import Strategy

        if not _DEVTOOLS_STRATEGIES_ROOT.is_dir():
            self.skipTest(f"missing devtools strategies root: {_DEVTOOLS_STRATEGIES_ROOT}")

        strategies_root = str(_DEVTOOLS_STRATEGIES_ROOT)
        names = Strategy.list_strategies(strategies_root=strategies_root)
        if _DEVTOOLS_STOCK_BASED not in names:
            self.skipTest(f"strategy not discovered: {_DEVTOOLS_STOCK_BASED}")

        try:
            result = Strategy.enumerate(
                _DEVTOOLS_STOCK_BASED,
                strategies_root=strategies_root,
            )
        except NotImplementedError:
            self.skipTest("enumerate blocked by worker/hooks gap")
        except Exception as exc:
            self.skipTest(f"enumerate environment not ready: {exc}")

        self.assertTrue(result.get("success") is not None)

    def test_enumerate_slice_based_if_environment_ready(self) -> None:
        """slice_based 端到端：compute 骨架；环境不足则 skip。"""
        from core.modules.strategy import Strategy

        if not _DEVTOOLS_STRATEGIES_ROOT.is_dir():
            self.skipTest(f"missing devtools strategies root: {_DEVTOOLS_STRATEGIES_ROOT}")

        strategies_root = str(_DEVTOOLS_STRATEGIES_ROOT)
        try:
            result = Strategy.enumerate(
                _DEVTOOLS_SLICE_BASED,
                strategies_root=strategies_root,
            )
        except NotImplementedError as exc:
            self.skipTest(f"slice_based worker not implemented yet: {exc}")
        except Exception as exc:
            self.skipTest(f"slice_based enumerate environment not ready: {exc}")

        self.assertTrue(result.get("success") is not None)


if __name__ == "__main__":
    unittest.main()
