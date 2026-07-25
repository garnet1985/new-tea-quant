"""价格回测 version 目录产物路径约定。

本文件:
- ReportPaths: 复用 simulation_output 文件名；补充 price 专有路径 helper
  边界: 负责路径；不负责写盘逻辑
"""
from __future__ import annotations

from pathlib import Path

from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITIES_SUBDIR,
    ENTITY_IDS_FILE,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
    RUNTIME_ENV_FILE,
)

PRICE_VERSION_REQUIRED_FILES = (
    RUNTIME_ENV_FILE,
    ENTITY_IDS_FILE,
    OVERALL_REPORT_FILE,
)


class ReportPaths:
    """价格回测产物路径。

    边界:
    - 负责: version 目录内文件名约定（共享常量 + price 专有 investments CSV）
    - 不负责: 写盘
    """

    @staticmethod
    def entities_dir(output_dir: Path) -> Path:
        return Path(output_dir) / ENTITIES_SUBDIR

    @staticmethod
    def runtime_env_path(output_dir: Path) -> Path:
        return Path(output_dir) / RUNTIME_ENV_FILE

    @staticmethod
    def entity_ids_path(output_dir: Path) -> Path:
        return Path(output_dir) / ENTITY_IDS_FILE

    @staticmethod
    def overall_report_path(output_dir: Path) -> Path:
        return Path(output_dir) / OVERALL_REPORT_FILE

    @staticmethod
    def performance_path(output_dir: Path) -> Path:
        return Path(output_dir) / PERFORMANCE_FILE

    @staticmethod
    def investments_csv(output_dir: Path, entity_id: str) -> Path:
        safe = str(entity_id or "").strip().replace("/", "_")
        return ReportPaths.entities_dir(output_dir) / f"{safe}_investments.csv"


__all__ = [
    "ENTITIES_SUBDIR",
    "ENTITY_IDS_FILE",
    "OVERALL_REPORT_FILE",
    "PERFORMANCE_FILE",
    "PRICE_VERSION_REQUIRED_FILES",
    "RUNTIME_ENV_FILE",
    "ReportPaths",
]
