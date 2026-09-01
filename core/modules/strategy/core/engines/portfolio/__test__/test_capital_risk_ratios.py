"""年化夏普 / Sortino：完整净值序列，rf = MAR = 0。"""
from __future__ import annotations

import math
import unittest

from core.modules.strategy.core.engines.portfolio.report_manager.capital_metrics import (
    EquityCurves,
    annualized_risk_ratios,
    annualized_sharpe,
    annualized_sortino,
    period_returns,
)


class TestPeriodReturns(unittest.TestCase):
    def test_adjacent_simple_returns(self) -> None:
        rets = period_returns([100.0, 101.0, 99.0])
        self.assertEqual(len(rets), 2)
        self.assertAlmostEqual(rets[0], 0.01)
        self.assertAlmostEqual(rets[1], (99.0 - 101.0) / 101.0)


class TestAnnualizedSharpeSortino(unittest.TestCase):
    def test_too_few_points_is_none(self) -> None:
        self.assertIsNone(annualized_sharpe([0.01]))
        self.assertIsNone(annualized_sortino([0.01]))
        sharpe, sortino = annualized_risk_ratios([100.0, 101.0])
        self.assertIsNone(sharpe)
        self.assertIsNone(sortino)

    def test_zero_vol_is_none(self) -> None:
        rets = [0.01, 0.01, 0.01]
        self.assertIsNone(annualized_sharpe(rets))

    def test_all_up_sortino_is_none(self) -> None:
        rets = [0.01, 0.02, 0.015]
        self.assertIsNone(annualized_sortino(rets))
        self.assertIsNotNone(annualized_sharpe(rets))

    def test_sharpe_equals_mean_over_sample_std_times_sqrt_252(self) -> None:
        rets = [0.01, -0.005, 0.015]
        mean = sum(rets) / 3
        var = sum((x - mean) ** 2 for x in rets) / 2
        expected = (mean / math.sqrt(var)) * math.sqrt(252.0)
        self.assertAlmostEqual(annualized_sharpe(rets) or 0.0, expected)

    def test_sortino_uses_full_sample_downside_squares(self) -> None:
        rets = [0.01, -0.005, 0.015]
        mean = sum(rets) / 3
        down = math.sqrt(sum(min(r, 0.0) ** 2 for r in rets) / 3)
        expected = (mean / down) * math.sqrt(252.0)
        self.assertAlmostEqual(annualized_sortino(rets) or 0.0, expected)

    def test_compute_uses_full_series_not_downsampled_chart(self) -> None:
        points = [{"date": str(i), "equity": 100.0 + (i % 7) - 3, "cash": 50.0, "open_positions": 1} for i in range(120)]
        curves = EquityCurves.compute(points, initial_capital=100.0)
        self.assertLessEqual(len(curves.equity_curve_values), 80)
        vals = [float(p["equity"]) for p in points]
        sharpe, sortino = annualized_risk_ratios(vals)
        self.assertEqual(curves.sharpe_ratio, sharpe)
        self.assertEqual(curves.sortino_ratio, sortino)


if __name__ == "__main__":
    unittest.main()
