#!/usr/bin/env python3
"""
Strategy 枚举定义
"""

from enum import Enum


class ExecutionMode(Enum):
    """执行模式"""
    SCAN = 'scan'          # 扫描模式
    SIMULATE = 'simulate'  # 模拟模式


class OpportunityStatus(Enum):
    """机会状态"""
    ACTIVE = 'active'      # 活跃（待回测，正在追踪中）
    TESTING = 'testing'    # 测试中
    CLOSED = 'closed'      # 已关闭（回测完成）
    EXPIRED = 'expired'    # 已失效
    OPEN = 'open'          # 枚举结束时仍有未完成的 target
    WIN = 'win'            # 所有 target 完成且 ROI > 0
    LOSS = 'loss'          # 所有 target 完成且 ROI <= 0


class SellReason(Enum):
    """卖出原因"""
    STOP_LOSS = 'stop_loss'        # 止损
    TAKE_PROFIT = 'take_profit'    # 止盈
    MAX_HOLDING = 'max_holding'    # 达到最大持有期
    END_OF_PERIOD = 'end_of_period'  # 回测期结束
