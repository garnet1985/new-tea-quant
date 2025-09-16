#!/usr/bin/env python3
"""
Simulator全局枚举定义
"""
from enum import Enum


class InvestmentResult(Enum):
    """投资结果枚举 - 通用枚举，适用于所有策略"""
    WIN = 'win'
    LOSS = 'loss'
    OPEN = 'open'
