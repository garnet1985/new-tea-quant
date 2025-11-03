#!/usr/bin/env python3
"""
组件模块 - 统一管理所有分析器组件
"""

# 核心组件
from app.data_loader import DataLoader  # 使用全局DataLoader
from .settings_validator import SettingsValidator
from .entity.investment import Investment 
from .entity.opportunity import Opportunity
from .entity.target import InvestmentTarget

# 数据处理器组件
from .indicators import Indicators

# 实体组件
# 枚举组件
from app.analyzer.enums import InvestmentResult

# 投资管理组件
from .investment.investment_recorder import InvestmentRecorder

# 模拟器组件
from .simulator.simulator import Simulator
from .simulator.services.preprocess_service import PreprocessService
from .simulator.services.simulating_service import SimulatingService
from .simulator.services.postprocess_service import PostprocessService

__all__ = [
    # 核心组件
    'DataLoader',
    'SettingsValidator',
    'Investment',
    'Opportunity',
    'InvestmentTarget',
    # 数据处理器组件
    'Indicators',
    
    # 枚举组件
    'InvestmentResult',
    
    # 投资管理组件
    'InvestmentRecorder',
    
    # 模拟器组件
    'Simulator',
    'PreprocessService',
    'SimulatingService', 
    'PostprocessService',
]
