"""API contract tests for modules.strategy Facade（对齐 API.md）。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy import Strategy
from core.modules.strategy.contracts import (
    AsOfSlice,
    CalendarAsOfResult,
    ExecutionMode,
    Investment,
    JobBundleLoader,
    Opportunity,
    ProgressRecorder,
    SellReason,
    SimulateKind,
    StrategyContext,
    StrategyHooks,
    WorkbenchStep,
)

pytestmark = pytest.mark.force_run


class TestStrategyApi(unittest.TestCase):
    def test_facade_export(self) -> None:
        import core.modules.strategy as pkg

        self.assertEqual(pkg.__all__, ["Strategy"])
        self.assertFalse(hasattr(pkg, "BackTestPipelines"))
        self.assertFalse(hasattr(pkg, "DiscoveryService"))

    def test_public_methods(self) -> None:
        for name in (
            "scan",
            "analyze",
            "enumerate",
            "price_factor",
            "portfolio",
            "simulate",
            "list_strategies",
            "list_enabled_strategies",
            "list_enabled_keys",
            "list_strategy_infos",
            "find",
            "get_strategy_info",
            "resolve",
            "resolve_folder",
            "load_price_entity_investments",
            "price_overall_report_path",
            "present_report",
            "is_valid_path",
            "clear_workbench_cache",
            "prune_simulation_results",
            "prune_scan_results",
            "export_package",
            "import_package",
            "latest_completed_trading_date",
        ):
            self.assertTrue(callable(getattr(Strategy, name)), name)

    def test_contracts_enums(self) -> None:
        self.assertEqual(SimulateKind.ENUMERATE.value, "enumerate")
        self.assertEqual(SimulateKind.PRICE_FACTOR.value, "price_factor")
        self.assertEqual(SimulateKind.PORTFOLIO.value, "portfolio")
        self.assertEqual(ExecutionMode.SCAN.value, "scan")
        self.assertEqual(SellReason.STOP_LOSS.value, "stop_loss")
        self.assertEqual(WorkbenchStep.ENUM.value, "enum")
        self.assertEqual(
            WorkbenchStep.PRICE.to_simulate_kind(), SimulateKind.PRICE_FACTOR
        )

    def test_contracts_hook_and_data_types(self) -> None:
        self.assertTrue(issubclass(StrategyHooks, object))
        self.assertEqual(StrategyContext.__name__, "StrategyContext")
        opp = Opportunity(stock={}, record_of_today={"close": 1.0})
        self.assertEqual(opp.trigger_price, 1.0)
        result = CalendarAsOfResult(as_of_date="20240102", stocks=[])
        self.assertEqual(result.session_state, {})
        self.assertTrue(Investment is not None)
        self.assertTrue(hasattr(AsOfSlice, "ready_date_by_entity"))
        self.assertTrue(hasattr(AsOfSlice, "slice_contracts"))
        self.assertTrue(hasattr(JobBundleLoader, "load"))
        self.assertTrue(hasattr(ProgressRecorder, "for_tag_run"))

    def test_list_strategies_delegates_to_discovery(self) -> None:
        info = MagicMock()
        info.id.return_value = "demo/x"
        info.unique_relative_path = "demo/x"
        info.key = "x"
        info.is_enabled = True
        info.display_name = "X"
        info.settings = {}
        info.resolved_folder.return_value = "/tmp/x"
        with patch(
            "core.modules.strategy.core.strategy.DiscoveryService.discover_strategies",
            return_value=[info],
        ) as discover:
            names = Strategy.list_strategies()
        discover.assert_called_once()
        self.assertEqual(names, ["demo/x"])

    def test_list_enabled_strategies_delegates(self) -> None:
        info = MagicMock()
        info.id.return_value = "demo/y"
        info.unique_relative_path = "demo/y"
        info.key = "y"
        info.is_enabled = True
        info.display_name = "Y"
        info.settings = {}
        info.resolved_folder.return_value = "/tmp/y"
        with patch(
            "core.modules.strategy.core.strategy.DiscoveryService.get_enabled_strategies",
            return_value=[info],
        ) as discover:
            names = Strategy.list_enabled_strategies()
            keys = Strategy.list_enabled_keys()
        discover.assert_called()
        self.assertEqual(names, ["demo/y"])
        self.assertEqual(keys, ["y"])

    def test_get_strategy_info_found_and_missing(self) -> None:
        info = MagicMock()
        info.id.return_value = "demo/z"
        info.unique_relative_path = "demo/z"
        info.key = "z"
        info.is_enabled = True
        info.display_name = "Z"
        info.folder = "/tmp/z"
        info.settings = {"a": 1}
        info.resolved_folder.return_value = "/tmp/z"
        with patch(
            "core.modules.strategy.core.strategy.DiscoveryService.discover_strategies",
            return_value=[info],
        ):
            found = Strategy.get_strategy_info("demo/z")
            by_key = Strategy.find("z")
            missing = Strategy.get_strategy_info("nope")
        self.assertEqual(found["key"], "z")
        self.assertEqual(found["unique_relative_path"], "demo/z")
        self.assertEqual(found["display_name"], "Z")
        self.assertEqual(by_key["key"], "z")
        self.assertIsNone(missing)
        with patch(
            "core.modules.strategy.core.strategy.DiscoveryService.get_enabled_strategies",
            return_value=[info],
        ):
            enabled = Strategy.find("z", enabled_only=True)
        self.assertEqual(enabled["key"], "z")

    def test_is_valid_path(self) -> None:
        self.assertTrue(Strategy.is_valid_path("demo/random_v1"))
        self.assertFalse(Strategy.is_valid_path("demo/市值"))
        self.assertFalse(Strategy.is_valid_path(""))

    def test_clear_workbench_cache_raises_on_failure(self) -> None:
        with patch(
            "core.modules.strategy.core.services.workbench_cache_clear.WorkbenchCacheClear.clear_all",
            return_value={"ok": False, "error": "存储不可用"},
        ):
            with self.assertRaises(RuntimeError):
                Strategy.clear_workbench_cache()

    def test_simulate_full_raises(self) -> None:
        with patch(
            "core.modules.strategy.core.strategy.DiscoveryService.find_strategy",
            return_value=MagicMock(),
        ):
            with self.assertRaises(ValueError):
                Strategy.simulate("any", kind=SimulateKind.FULL)


if __name__ == "__main__":
    unittest.main()
