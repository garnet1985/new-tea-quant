#!/usr/bin/env python3
# MARK: STALE — 依赖已 UNUSED 的 SliceBasedCompute；热路径改 SliceEnumerationSimulator。
"""slice_based 集成：period_end force_exit + 真实 hooks（合成 K 线，不依赖行情库）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

pytest.skip(
    "MARK: STALE — SliceBasedCompute archived as UNUSED",
    allow_module_level=True,
)

# from core.modules.strategy.core.engines.enumerator.slice_based.compute import (
#     SliceBasedCompute,
#     _EntitySliceState,
# )
# from core.modules.strategy.core.engines.enumerator.slice_based.state.holdings import EntityHoldings
from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
from core.modules.strategy.core.services.discovery.discovery_service import DiscoveryService

_DEVTOOLS_STRATEGIES_ROOT = (
    Path(__file__).resolve().parents[4]
    / "devtools"
    / "performance"
    / "strategy"
    / "test_base_strategies"
)
_SLICE_STRATEGY = "slice_based"

_OPEN_DATES = ["20240102", "20241231"]
_STOCK_IDS = ["600000.SH", "600036.SH"]


def _bar(date: str, close: float) -> Dict[str, Any]:
    return {
        "date": date,
        "open": close,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
    }


def _klines_for_stock() -> List[Dict[str, Any]]:
    return [_bar(_OPEN_DATES[0], 3.0), _bar(_OPEN_DATES[1], 3.5)]


class _FakeEntityDataLoader:
    def __init__(
        self,
        *,
        stock_id: str,
        settings: Dict[str, Any],
        global_data: Dict[str, Any] | None = None,
        contract_cache: Any = None,
    ) -> None:
        _ = settings, global_data, contract_cache
        self.stock_id = stock_id
        self._klines = _klines_for_stock()

    def load(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def data_until(self, as_of: str) -> Dict[str, Any]:
        rows = [row for row in self._klines if str(row["date"]) <= str(as_of)]
        return {"stock.kline.daily": rows}

    def clear_working_state(self) -> None:
        return None


def _slice_settings() -> Dict[str, Any]:
    return {
        "market_profile": "china_a_stock",
        "core": {
            "universe_mode": "pit",
            "rebalance_period": "year",
            "min_close": 1.0,
            "max_close": 5.0,
            "top_n": 20,
            "cap_filter": "none",
            "start_date": "20240101",
            "end_date": "20241231",
        },
        "data": {
            "base": {
                "data_key": "stock.kline.daily",
                "params": {"adjust": "qfq"},
                "indicators": {},
            },
            "required": [],
            "min_required_records": 1,
        },
        "simulation": {
            "execution": {
                "mode": "slice_based",
            },
            "assumption": {
                "template": "custom",
                "tradability": {
                    "monitor_price": "close",
                    "enter_price": "close",
                    "exit_price": "close",
                },
            },
            "risk_control": {},
        },
        "goal": {"is_customized": True},
    }


def _build_compute_payload(*, output_dir: str, worker_ref: Dict[str, str]) -> Dict[str, Any]:
    return {
        "strategy_name": _SLICE_STRATEGY,
        "settings": _slice_settings(),
        "start_date": "20240101",
        "end_date": "20241231",
        "output_dir": output_dir,
        "stock_ids": list(_STOCK_IDS),
        "global_data": {"stock_list": list(_STOCK_IDS)},
        "backtest_calendar": {
            "market": "SSE",
            "period_start": "20240101",
            "period_end": "20241231",
            "open_dates": list(_OPEN_DATES),
        },
        "worker_module_path": worker_ref["worker_module_path"],
        "worker_class_name": worker_ref["worker_class_name"],
        "worker_file_path": worker_ref.get("worker_file_path", ""),
        "enumeration_execution_mode": "slice_based",
    }


class TestSlicePeriodEndIntegration(unittest.TestCase):
    """周期末 force_exit：开仓日 scan → 年末 period_end 平仓。"""

    @classmethod
    def setUpClass(cls) -> None:
        if not _DEVTOOLS_STRATEGIES_ROOT.is_dir():
            cls.worker_ref = {}
            return
        discovered = DiscoveryService.discover_strategies(_DEVTOOLS_STRATEGIES_ROOT)
        info = discovered.get(_SLICE_STRATEGY)
        if info is None:
            cls.worker_ref = {}
            return
        cls.worker_ref = {
            "worker_module_path": info["worker_module_path"],
            "worker_class_name": info["worker_class_name"],
            "worker_file_path": str(info.get("worker_file_path") or ""),
        }

    def setUp(self) -> None:
        if not self.worker_ref:
            self.skipTest(f"missing devtools strategy: {_SLICE_STRATEGY}")

    def _fake_hydrate(self, compute: SliceBasedCompute) -> None:
        for stock_id in compute.stock_ids:
            compute._states[stock_id] = _EntitySliceState(
                stock_id=stock_id,
                stock_info={"id": stock_id, "name": stock_id},
                data_loader=_FakeEntityDataLoader(
                    stock_id=stock_id,
                    settings=compute.settings.to_dict(),
                    global_data=compute.job_payload["global_data"],
                ),
                holdings=EntityHoldings(),
            )
        compute._stock_list = list(_STOCK_IDS)

    def test_period_end_force_exit_via_compute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = _build_compute_payload(
                output_dir=tmp,
                worker_ref=self.worker_ref,
            )
            compute = SliceBasedCompute(payload)
            with patch.object(compute, "_hydrate_entity_data", lambda: self._fake_hydrate(compute)):
                result = compute.run()

            self.assertTrue(result["success"])
            self.assertEqual(result["open_dates_processed"], len(_OPEN_DATES))

            completed: List[Dict[str, Any]] = []
            for row in result["stock_results"]:
                self.assertTrue(row["success"])
                for opp in row["opportunities"]:
                    if opp.get("outcome") == "completed":
                        completed.append(opp)

            self.assertGreaterEqual(len(completed), 1, "周期初应至少产生一笔持仓并在年末平仓")
            for opp in completed:
                self.assertEqual(opp["sell_reason"], "period_end")
                self.assertEqual(opp["outcome"], "completed")
                self.assertGreater(float(opp["sell_price"]), 0.0)

            csv_rows = OpportunityCsvHelper.collect_from_dir(Path(tmp))
            csv_completed = [row for row in csv_rows if row.get("outcome") == "completed"]
            self.assertEqual(len(csv_completed), len(completed))
            for row in csv_completed:
                self.assertEqual(row["sell_reason"], "period_end")


class TestSliceEnumerateIntegration(unittest.TestCase):
    """端到端 enumerate：有行情环境则断言 period_end；否则 skip。"""

    def test_enumerate_slice_period_end_when_data_available(self) -> None:
        from core.modules.strategy import Strategy

        if not _DEVTOOLS_STRATEGIES_ROOT.is_dir():
            self.skipTest(f"missing devtools strategies root: {_DEVTOOLS_STRATEGIES_ROOT}")

        strategies_root = str(_DEVTOOLS_STRATEGIES_ROOT)
        try:
            result = Strategy.enumerate(_SLICE_STRATEGY, strategies_root=strategies_root)
        except Exception as exc:
            self.skipTest(f"slice enumerate environment not ready: {exc}")

        self.assertTrue(result.get("success"))
        if int(result.get("total_opportunities") or 0) == 0:
            self.skipTest("no opportunities produced (market data unavailable for stock_pool)")

        from core.infra.project_context import ProjectContext

        output_dir = ProjectContext.path.get_strategy_directory_simulation_enum(_SLICE_STRATEGY) / "1"
        rows = OpportunityCsvHelper.collect_from_dir(output_dir)
        completed = [row for row in rows if row.get("outcome") == "completed"]
        self.assertGreater(len(completed), 0)
        for row in completed:
            self.assertEqual(row["sell_reason"], "period_end")


if __name__ == "__main__":
    unittest.main()
