"""统计计算纯工具（触发率）。

本文件:
- StatisticsHelper: 无外部依赖的汇总公式
  边界: 负责数值统计；不负责读 opportunities 文件或写报告
"""

from __future__ import annotations


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


__all__ = ["StatisticsHelper"]
