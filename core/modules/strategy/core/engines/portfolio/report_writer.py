"""兼容入口：PortfolioReportWriter → report_manager.ReportManager。"""
from core.modules.strategy.core.engines.portfolio.report_manager import (
    PortfolioReportHandle,
    PortfolioReportWriter,
    ReportManager,
)

__all__ = ["PortfolioReportWriter", "PortfolioReportHandle", "ReportManager"]
