#!/usr/bin/env python3
"""
结果展示模块

负责格式化展示 PriceFactorSimulator 的结果
"""

from typing import Dict, Any
from core.utils.icon.icon_service import IconService


class ResultPresenter:
    """结果展示器"""

    @staticmethod
    def present_results(session_summary: Dict[str, Any], strategy_name: str) -> None:
        """
        展示 PriceFactorSimulator 的结果（类似 legacy 的展示方式）
        
        Args:
            session_summary: 会话汇总结果
            strategy_name: 策略名称
        """
        if not session_summary:
            return

        print("\n" + "=" * 60)
        print(f"📊 {strategy_name} 策略价格因子回测结果")
        print("=" * 60)

        win_rate = session_summary.get("win_rate", 0)
        annual_return = session_summary.get("annual_return", 0)
        annual_return_in_trading_days = session_summary.get("annual_return_in_trading_days", 0)
        avg_roi = session_summary.get("avg_roi", 0) * 100.0  # 转换为百分比

        # 胜率
        if win_rate >= 50:
            win_rate_dot = IconService.get("green_dot")
        else:
            win_rate_dot = IconService.get("red_dot")
        print(f"{win_rate_dot} 胜率: {win_rate:.1f}%")

        # 平均 ROI
        if avg_roi >= 5:
            avg_roi_dot = IconService.get("green_dot")
        else:
            avg_roi_dot = IconService.get("red_dot")
        print(f"{avg_roi_dot} 平均每笔投资回报率(ROI): {avg_roi:.2f}%")

        # 年化收益率
        if annual_return >= 0.15:
            annual_return_dot = IconService.get("green_dot")
        else:
            annual_return_dot = IconService.get("red_dot")

        if annual_return_in_trading_days >= 0.1:
            annual_return_in_trading_days_dot = IconService.get("green_dot")
        else:
            annual_return_in_trading_days_dot = IconService.get("red_dot")

        print("折算后平均每笔投资年化收益率: ")
        print(f" - {annual_return_dot} 按自然日: {annual_return * 100:.2f}%")
        print(f" - {annual_return_in_trading_days_dot} 按交易日: {annual_return_in_trading_days * 100:.2f}%")

        # 其他统计信息
        print(f"{IconService.get('clock')} 平均投资时长: {session_summary.get('avg_duration_in_days', 0):.1f} 自然日")
        print(f"{IconService.get('bar_chart')} 总投资次数: {session_summary.get('total_investments', 0)}")
        print(f"{IconService.get('success')} 成功次数: {session_summary.get('total_win_investments', 0)}")
        print(f"{IconService.get('error')} 失败次数: {session_summary.get('total_loss_investments', 0)}")
        print(f"{IconService.get('ongoing')} 未完成次数: {session_summary.get('total_open_investments', 0)}")
        
        # 总盈利
        total_profit = session_summary.get("total_profit", 0.0)
        if total_profit >= 0:
            profit_icon = IconService.get("green_dot")
        else:
            profit_icon = IconService.get("red_dot")
        print(f"{profit_icon} 总盈利: {total_profit:.2f}")
        
        # 产生机会的股票数
        stocks_with_opportunities = session_summary.get("stocks_have_opportunities", 0)
        print(f"{IconService.get('money')} 产生机会的股票数: {stocks_with_opportunities}")
        
        print("")


