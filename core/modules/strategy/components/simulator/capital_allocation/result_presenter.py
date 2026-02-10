#!/usr/bin/env python3
"""
资金分配模拟器结果展示模块

负责格式化展示 CapitalAllocationSimulator 的整体结果（策略级）。
"""

from typing import Dict, Any
from core.utils.icon.icon_service import IconService


class CapitalAllocationResultPresenter:
    """CapitalAllocationSimulator 结果展示器"""

    @staticmethod
    def present_results(summary: Dict[str, Any], strategy_name: str) -> None:
        """
        展示资金分配模拟的结果。

        Args:
            summary: summary_strategy.json 对应的汇总字典
            strategy_name: 策略名称
        """
        if not summary:
            return

        initial_capital = summary.get("initial_capital", 0.0)
        final_equity = summary.get("final_total_equity", summary.get("final_equity", 0.0))
        total_return = summary.get("total_return", 0.0)
        max_drawdown = summary.get("max_drawdown", 0.0)

        total_trades = summary.get("total_trades", 0)
        buy_trades = summary.get("buy_trades", 0)
        sell_trades = summary.get("sell_trades", 0)
        win_trades = summary.get("win_trades", 0)
        loss_trades = summary.get("loss_trades", 0)
        win_rate = summary.get("win_rate", 0.0) * 100.0

        print("\n" + "=" * 60)
        print(f"💰 {strategy_name} 策略资金分配回测结果")
        print("=" * 60)

        # 资金概况
        print(f"{IconService.get('money')} 初始资金 (Initial capital): {initial_capital:,.2f}")
        print(f"{IconService.get('money')} 最终总资产 (Final total equity): {final_equity:,.2f}")
        print(f"{IconService.get('bar_chart')} 总收益率 (Total return): {total_return * 100:.2f}%")
        print(f"{IconService.get('warning')} 最大回撤 (Max drawdown): {max_drawdown * 100:.2f}%")

        # 交易统计
        print(f"\n{IconService.get('bar_chart')} 交易统计:")
        print(f"  总交易次数: {total_trades} (买入: {buy_trades}, 卖出: {sell_trades})")
        print(f"  盈利交易: {win_trades}, 亏损交易: {loss_trades}")
        print(f"  交易胜率: {win_rate:.2f}%")

        print("")

