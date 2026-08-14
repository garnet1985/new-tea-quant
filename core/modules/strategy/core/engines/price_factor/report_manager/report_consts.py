"""价格回测 version 目录产物路径约定。"""
from __future__ import annotations

from pathlib import Path

from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITIES_SUBDIR,
    ENTITY_IDS_FILE,
    ENTITY_LIST_FILE,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
    PRICE_INVESTMENTS_SUFFIX,
    PRICE_REPORT_FILES,
    PRICE_VERSION_REQUIRED_FILES,
    RUNTIME_ENV_FILE,
)


class ReportPaths:
    """价格回测产物路径。"""

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
    def entity_list_path(output_dir: Path) -> Path:
        return Path(output_dir) / ENTITY_LIST_FILE

    @staticmethod
    def performance_path(output_dir: Path) -> Path:
        return Path(output_dir) / PERFORMANCE_FILE

    @staticmethod
    def investments_csv(output_dir: Path, entity_id: str) -> Path:
        safe = str(entity_id or "").strip().replace("/", "_")
        return ReportPaths.entities_dir(output_dir) / f"{safe}{PRICE_INVESTMENTS_SUFFIX}"


__all__ = [
    "PRICE_REPORT_FILES",
    "PRICE_VERSION_REQUIRED_FILES",
    "ReportPaths",
]
