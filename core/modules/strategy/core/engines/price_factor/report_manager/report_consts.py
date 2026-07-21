"""价格回测 version 目录产物路径约定。"""
from __future__ import annotations

from pathlib import Path

GLOBAL_PREFIX = "0_"
RUNTIME_ENV_FILE = f"{GLOBAL_PREFIX}runtime_env.json"
ENTITY_IDS_FILE = f"{GLOBAL_PREFIX}entity_ids.txt"
PERFORMANCE_FILE = f"{GLOBAL_PREFIX}performance.json"
OVERALL_REPORT_FILE = f"{GLOBAL_PREFIX}overall_report.json"

ENTITIES_SUBDIR = "entities"

PRICE_VERSION_REQUIRED_FILES = (
    RUNTIME_ENV_FILE,
    ENTITY_IDS_FILE,
    OVERALL_REPORT_FILE,
)


class ReportPaths:
    """价格回测产物路径。

    边界:
    - 负责: version 目录内文件名约定
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
