#!/usr/bin/env python3
import unittest

from core.modules.strategy.engines.shared.performance_profiler import (
    AggregateProfiler,
    PerformanceMetrics,
    PerformanceProfiler,
    REPORT_SCHEMA_VERSION,
)


class TestPerformanceProfiler(unittest.TestCase):
    def test_metrics_roundtrip_v2(self):
        profiler = PerformanceProfiler("000001.SZ")
        profiler.metrics.time_load_contracts = 0.5
        profiler.metrics.time_enumerate = 0.2
        profiler.metrics.time_total = 0.8
        profiler.metrics.storage_load_calls = 2
        profiler.metrics.storage_load_time = 0.45
        profiler.metrics.storage_loads_by_slot = {"klines": 0.4, "extras": 0.05}
        payload = profiler.finalize().to_dict()
        self.assertEqual(payload["schema_version"], REPORT_SCHEMA_VERSION)
        self.assertNotIn("io", payload)
        self.assertEqual(payload["load_path"], "")
        restored = PerformanceMetrics.from_dict(payload)
        self.assertAlmostEqual(restored.time_load_contracts, 0.5)
        self.assertEqual(restored.storage_load_calls, 2)
        self.assertAlmostEqual(restored.storage_loads_by_slot["klines"], 0.4)
        self.assertEqual(PerformanceMetrics.from_dict({"schema_version": 1}), PerformanceMetrics())

    def test_aggregate_summary_pct(self):
        agg = AggregateProfiler()
        for sid, load_c, enum in (
            ("A", 0.8, 0.1),
            ("B", 0.7, 0.15),
        ):
            m = PerformanceMetrics(stock_id=sid)
            m.time_load_contracts = load_c
            m.time_enumerate = enum
            m.time_total = load_c + enum
            m.storage_load_time = load_c
            agg.add_stock_metrics(sid, m)
        summary = agg.get_summary()
        pct = summary["time_breakdown"]["pct_of_worker_total"]
        self.assertGreater(pct["load_contracts"], pct["enumerate"])
        self.assertEqual(summary["time_breakdown"]["dominant_phase"], "load_contracts")
        self.assertEqual(summary["report_kind"], "aggregate")
        self.assertNotIn("io", summary)
        self.assertIn("parallelism_factor", summary["summary"])


if __name__ == "__main__":
    unittest.main()
