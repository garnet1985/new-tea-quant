"""
BFF APIs 模块
按业务拆分不同的API
"""
from .health import health_api_bp
from .setup import setup_api_bp, SetupService, SetupRuntimeManager
from .strategy_workbench import strategy_workbench_api_bp, StrategyWorkbenchService

__all__ = [
    'SetupService',
    'SetupRuntimeManager',
    'StrategyWorkbenchService',
    'health_api_bp',
    'setup_api_bp',
    'strategy_workbench_api_bp',
]

