"""仿真 version 产物路径定位（布局服务）。

消费者: enumerator, price_factor, portfolio
边界: 拼路径 / 扫文件名；不解析 CSV/JSON 业务字段
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITIES_SUBDIR,
    ENTITY_IDS_FILE,
    ENTITY_LIST_FILE,
    GOAL_ACHIEVEMENTS_SUFFIX,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
    RUNTIME_ENV_FILE,
    STOCK_INVESTMENTS_SUFFIX,
)


class ArtifactPaths:
    """version 目录内路径约定。"""

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
    def stock_investments_path(output_dir: Path, entity_id: str) -> Path:
        eid = str(entity_id or "").strip()
        return ArtifactPaths.entities_dir(output_dir) / f"{eid}{STOCK_INVESTMENTS_SUFFIX}"

    @staticmethod
    def goal_achievements_path(output_dir: Path, entity_id: str) -> Path:
        eid = str(entity_id or "").strip()
        return ArtifactPaths.entities_dir(output_dir) / f"{eid}{GOAL_ACHIEVEMENTS_SUFFIX}"

    @staticmethod
    def collect_entity_ids_from_stock_investments(output_dir: Path) -> List[str]:
        """按 ``*_stock_investments.csv`` 文件名收集 entity_id（先 entities/ 再根目录）。"""
        nested = ArtifactPaths._scan_suffix(
            ArtifactPaths.entities_dir(output_dir), STOCK_INVESTMENTS_SUFFIX
        )
        if nested:
            return nested
        return ArtifactPaths._scan_suffix(Path(output_dir), STOCK_INVESTMENTS_SUFFIX)

    @staticmethod
    def _scan_suffix(directory: Path, suffix: str) -> List[str]:
        if not directory.is_dir():
            return []
        return sorted(
            entry.name[: -len(suffix)]
            for entry in directory.iterdir()
            if entry.is_file() and entry.name.endswith(suffix)
        )


# 兼容旧调用名
ReportPaths = ArtifactPaths

__all__ = ["ArtifactPaths", "ReportPaths"]
