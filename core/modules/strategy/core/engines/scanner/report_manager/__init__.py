"""Scanner run 产物：ReportManager 为对外入口。"""
from .report_manager import ReportManager
from .scan_summary import ScanSummary

__all__ = ["ReportManager", "ScanSummary"]
