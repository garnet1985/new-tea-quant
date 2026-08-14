"""Portfolio version 目录产物路径。"""
from __future__ import annotations

from pathlib import Path

from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITY_LIST_FILE,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
    RUNTIME_ENV_FILE,
)

TRADES_FILE = "trades.json"
EQUITY_CURVE_FILE = "equity_curve.json"

PORTFOLIO_REPORT_FILES = (
    OVERALL_REPORT_FILE,
    ENTITY_LIST_FILE,
    PERFORMANCE_FILE,
)
PORTFOLIO_VERSION_REQUIRED_FILES = (
    RUNTIME_ENV_FILE,
    *PORTFOLIO_REPORT_FILES,
)


class ReportPaths:
    """Portfolio 产物路径。"""

    @staticmethod
    def runtime_env_path(output_dir: Path) -> Path:
        return Path(output_dir) / RUNTIME_ENV_FILE

    @staticmethod
    def overall_report_path(output_dir: Path) -> Path:
        return Path(output_dir) / OVERALL_REPORT_FILE

    @staticmethod
    def entity_list_path(output_dir: Path) -> Path:
        return Path(output_dir) / ENTITY_LIST_FILE

    @staticmethod
    def performance_path(output_dir: Path) -> Path:
        return Path(output_dir) / PERFORMANCE_FILE

    @staticmethod
    def trades_path(output_dir: Path) -> Path:
        return Path(output_dir) / TRADES_FILE

    @staticmethod
    def equity_curve_path(output_dir: Path) -> Path:
        return Path(output_dir) / EQUITY_CURVE_FILE


__all__ = [
    "EQUITY_CURVE_FILE",
    "PORTFOLIO_REPORT_FILES",
    "PORTFOLIO_VERSION_REQUIRED_FILES",
    "ReportPaths",
    "TRADES_FILE",
]
