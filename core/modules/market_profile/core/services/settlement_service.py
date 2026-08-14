#!/usr/bin/env python3
"""交收规则服务（Settlement Service）。"""


class SettlementService:
    """交收规则服务。

    为所有公有方法提供交收规则计算功能。
    """

    @staticmethod
    def is_allowed_to_settle(days_held: int, t_plus: int) -> bool:
        """判断是否允许卖出（交收规则）。

        Args:
            days_held: 持有天数（从买入日起）
            t_plus: T+N交收周期

        Returns:
            True表示允许卖出
        """
        return days_held >= t_plus

    @staticmethod
    def get_settlement_period(t_plus: int) -> int:
        """获取交收周期（T+N）"""
        return t_plus


__all__ = ["SettlementService"]