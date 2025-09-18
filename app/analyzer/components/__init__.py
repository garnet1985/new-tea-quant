#!/usr/bin/env python3
"""
组件模块 - 统一管理所有分析器组件
"""

# 核心组件
from .data_loader import DataLoader
from .settings_validator import SettingsValidator

# 数据处理器组件
from .data_processor.indicators import Indicators

# 实体组件
from .entity.entity_builder import EntityBuilder

# 枚举组件
from .enum.common_enum import InvestmentResult

# 投资管理组件
from .investment.investment_goal_manager import InvestmentGoalManager
from .investment.investment_recorder import InvestmentRecorder

# 模拟器组件
from .simulator.simulator import Simulator
from .simulator.services.preprocess_service import PreprocessService
from .simulator.services.simulating_service import SimulatingService
from .simulator.services.postprocess_service import PostprocessService

__all__ = [
    # 核心组件
    'DataLoader',
    'ScanExecutor', 
    'SettingsValidator',
    'StrategyExecutor', 
    
    # 数据处理器组件
    'Indicators',
    
    # 实体组件
    'EntityBuilder',
    
    # 枚举组件
    'InvestmentResult',
    
    # 投资管理组件
    'InvestmentGoalManager',
    'InvestmentRecorder',
    
    # 模拟器组件
    'Simulator',
    'PreprocessService',
    'SimulatingService', 
    'PostprocessService',
]
