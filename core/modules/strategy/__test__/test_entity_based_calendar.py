#!/usr/bin/env python3
"""entity_based：按 open_dates 推进，仅新 base bar 日 scan。"""
from __future__ import annotations

import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from core.modules.strategy.core.engines.enumerator.entity_based.execute_payload import (
    EntityBasedExecutePayload,
)
from core.modules.strategy.core.engines.enumerator.entity_based.executor import EntityBasedExecutor
from core.modules.strategy.core.engines.shared.data_class import Opportunity

_BASE = "stock.kline.daily"
_OPEN_DATES = ["20240102", "20240103", "20240104", "20240105"]
_ENTITY = "600000.SH"


def _bar(date: str, close: float) -> Dict[str, Any]:
    return {
        "date": date,
        "open": close,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
    }


class _FakeLoader:
    def __init__(self, bars: List[Dict[str, Any]]) -> None:
        self._bars = list(bars)

    def data_until(self, as_of: str) -> Dict[str, Any]:
        rows = [b for b in self._bars if str(b["date"]) <= str(as_of)]
        return {_BASE: rows}


class _FakeSession:
    def __init__(self, loader: _FakeLoader) -> None:
        self._loader = loader

    def loader_for(self, entity_id: str) -> _FakeLoader:
        return self._loader


def _minimal_payload(*, open_dates: List[str]) -> EntityBasedExecutePayload:
    return EntityBasedExecutePayload.from_mapping(
        {
            "entity_id": _ENTITY,
            "strategy_name": "demo/test",
            "settings": {
                "is_enabled": True,
                "data": {
                    "base": {"data_key": _BASE, "params": {}},
                    "min_required_records": 2,
                },
            },
            "start_date": "20240102",
            "end_date": "20240105",
            "output_dir": "/tmp/out",
            "global_data": {"stock_list": [_ENTITY]},
            "open_dates": open_dates,
            "backtest_calendar": {"open_dates": open_dates, "market": "SSE"},
            "worker_module_path": "mod",
            "worker_class_name": "Hooks",
        }
    )


class TestEntityBasedCalendarExecutor(unittest.TestCase):
    def test_scans_only_on_new_base_bar_days(self) -> None:
        # 20240104 日历开市但无新 K 线（末根仍为 20240103）
        bars = [
            _bar("20240102", 10.0),
            _bar("20240103", 10.5),
            _bar("20240105", 11.0),
        ]
        loader = _FakeLoader(bars)
        session = _FakeSession(loader)
        payload = _minimal_payload(open_dates=_OPEN_DATES)
        executor = EntityBasedExecutor(payload, session=session)

        scan_dates: List[str] = []

        def _fake_scan(*, as_of: str, **kwargs: Any) -> Optional[Opportunity]:
            scan_dates.append(as_of)
            return None

        with patch(
            "core.modules.strategy.core.engines.enumerator.entity_based.executor.StockMetaHelper.load",
            return_value={"name": "Test"},
        ), patch(
            "core.modules.strategy.core.engines.enumerator.entity_based.executor.StrategyHookRuntime.from_job_payload",
            return_value=MagicMock(),
        ), patch.object(executor, "_invoke_scan_hooks", side_effect=_fake_scan):
            result = executor.execute()

        self.assertTrue(result["success"])
        self.assertEqual(scan_dates, ["20240103", "20240105"])

    def test_warmup_skips_until_min_required(self) -> None:
        bars = [_bar("20240102", 10.0)]
        loader = _FakeLoader(bars)
        session = _FakeSession(loader)
        payload = _minimal_payload(open_dates=["20240102", "20240103"])
        executor = EntityBasedExecutor(payload, session=session)

        with patch(
            "core.modules.strategy.core.engines.enumerator.entity_based.executor.StockMetaHelper.load",
            return_value={"name": "Test"},
        ), patch(
            "core.modules.strategy.core.engines.enumerator.entity_based.executor.StrategyHookRuntime.from_job_payload",
            return_value=MagicMock(),
        ), patch.object(executor, "_invoke_scan_hooks") as scan_mock:
            executor.execute()

        scan_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
