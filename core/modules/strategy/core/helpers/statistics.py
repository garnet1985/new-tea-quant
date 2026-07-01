"""统计计算纯工具。"""

from __future__ import annotations

from typing import Any, Dict, List


class StatisticsHelper:
    """统计公式工具（无外部模块依赖）。"""

    @staticmethod
    def calculate_trigger_ratio(trigger_stocks: int, total_stocks: int) -> float:
        return (trigger_stocks / total_stocks) if total_stocks > 0 else 0.0

    @staticmethod
    def calculate_avg_per_stock(total_opportunities: int, trigger_stocks: int) -> float:
        return (total_opportunities / trigger_stocks) if trigger_stocks > 0 else 0.0

    @staticmethod
    def calculate_completed_ratio(completed_count: int, total_count: int) -> float:
        return (completed_count / total_count) if total_count > 0 else 0.0

    @staticmethod
    def calculate_avg(values: List[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def calculate_percentile(values: List[float], percentile: float) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        k = (n - 1) * percentile / 100.0
        f = int(k)
        c = f + 1 if f + 1 < n else f
        if f == c:
            return sorted_values[f]
        d0 = sorted_values[f] * (c - k)
        d1 = sorted_values[c] * (k - f)
        return d0 + d1

    @staticmethod
    def group_by_stock(opportunities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for opp in opportunities:
            stock_id = opp.get("stock_id", "")
            if stock_id:
                grouped.setdefault(stock_id, []).append(opp)
        return grouped

    @staticmethod
    def extract_roi_values(simulations: List[Dict[str, Any]]) -> List[float]:
        roi_values: List[float] = []
        for sim in simulations:
            roi = sim.get("roi", 0.0)
            if isinstance(roi, (int, float)):
                roi_values.append(float(roi))
        return roi_values

    @staticmethod
    def extract_holding_days(simulations: List[Dict[str, Any]]) -> List[float]:
        holding_days: List[float] = []
        for sim in simulations:
            days = sim.get("holding_days", 0)
            if isinstance(days, (int, float)):
                holding_days.append(float(days))
        return holding_days


__all__ = ["StatisticsHelper"]
