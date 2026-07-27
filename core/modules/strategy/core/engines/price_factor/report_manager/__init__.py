"""价格回测 run 产物：ReportManager 为对外入口。"""
from core.modules.strategy.core.engines.price_factor.report_manager.report_manager import (
    ReportManager,
    SavedRunArtifacts,
)

__all__ = [
    "ReportManager",
    "SavedRunArtifacts",
]
