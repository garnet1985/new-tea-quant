"""
跨表备份与恢复服务（BackupAndRestoreService）。

定位：
- 统一封装 DataManager 维度的备份/恢复入口；
- 具体单表导出/导入能力复用 DbBaseModel.export_data/import_data；
- 支持按日期目录自动清理旧备份。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .. import BaseDataService
from core.infra.project_context import PathManager


logger = logging.getLogger(__name__)

DATE_FMT = "%Y%m%d"


@dataclass
class BackupResult:
    table: str
    files: List[Path]


class BackupAndRestoreService(BaseDataService):
    """DataManager 维度的跨表备份/恢复服务。"""

    def __init__(self, data_manager):
        super().__init__(data_manager)

    def _default_backup_root(self) -> Path:
        return PathManager.backup_data()

    def _resolve_backup_dir(self, root_dir: Optional[str | Path], backup_date: Optional[str]) -> Path:
        base = Path(root_dir) if root_dir else self._default_backup_root()
        bdate = backup_date or date.today().strftime(DATE_FMT)
        if not re.fullmatch(r"\d{8}", bdate):
            raise ValueError(f"backup_date 格式错误: {bdate}，应为 YYYYMMDD")
        backup_dir = base / bdate
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def _normalize_table_names(self, tables: Optional[Sequence[str]]) -> List[str]:
        if tables:
            return sorted({t.strip() for t in tables if t and t.strip()})
        return sorted(self.data_manager._table_cache.keys())

    def backup(
        self,
        *,
        tables: Optional[Sequence[str]] = None,
        root_dir: Optional[str | Path] = None,
        backup_date: Optional[str] = None,
        archive_format: str = "tar.gz",
        condition: str = "1=1",
        params: tuple = (),
        keep: int = 3,
    ) -> List[BackupResult]:
        """
        备份单表或多表（跨表入口）。

        Args:
            tables: 要备份的表名；不传则备份 DataManager 已注册的全部表
            root_dir: 备份根目录，默认 userspace/backup/data
            backup_date: 备份日期目录名 YYYYMMDD，默认当天
            archive_format: 归档格式（tar.gz/zip）
            condition/params: 传给 model.export_data 的过滤条件
            keep: 备份完成后保留最近 N 个日期目录（<=0 表示不清理）
        """
        names = self._normalize_table_names(tables)
        backup_dir = self._resolve_backup_dir(root_dir, backup_date)
        results: List[BackupResult] = []

        for table_name in names:
            model = self.data_manager.get_table(table_name)
            if model is None:
                logger.warning("表未注册，跳过备份: %s", table_name)
                continue
            files = model.export_data(
                output_dir=backup_dir / table_name,
                archive_format=archive_format,
                condition=condition,
                params=params,
            )
            results.append(BackupResult(table=table_name, files=files))

        if keep > 0:
            self.prune_old_backups(root_dir=root_dir, keep=keep)
        return results

    def restore(
        self,
        *,
        backup_date: str,
        tables: Optional[Sequence[str]] = None,
        root_dir: Optional[str | Path] = None,
        mode: str = "overwrite",
        target_table_map: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """
        从指定日期目录恢复单表或多表。
        """
        base = Path(root_dir) if root_dir else self._default_backup_root()
        if not re.fullmatch(r"\d{8}", backup_date):
            raise ValueError(f"backup_date 格式错误: {backup_date}，应为 YYYYMMDD")
        backup_dir = base / backup_date
        if not backup_dir.exists():
            raise FileNotFoundError(f"备份目录不存在: {backup_dir}")

        names = self._normalize_table_names(tables)
        restored: List[str] = []
        table_map = target_table_map or {}

        for table_name in names:
            model = self.data_manager.get_table(table_name)
            if model is None:
                logger.warning("表未注册，跳过恢复: %s", table_name)
                continue

            table_dir = backup_dir / table_name
            files = sorted(table_dir.glob("*.tar.gz")) + sorted(table_dir.glob("*.zip")) + sorted(table_dir.glob("*.csv"))
            if not files:
                logger.warning("未找到表备份文件，跳过恢复: %s (%s)", table_name, table_dir)
                continue

            model.import_data(
                files=files,
                mode=mode,
                target_table=table_map.get(table_name),
            )
            restored.append(table_name)

        return restored

    def prune_old_backups(self, *, root_dir: Optional[str | Path] = None, keep: int = 3) -> List[str]:
        """
        按 YYYYMMDD 目录名清理旧备份，仅保留最近 keep 个日期目录。
        """
        if keep <= 0:
            return []
        base = Path(root_dir) if root_dir else self._default_backup_root()
        if not base.exists():
            return []

        candidates = [p for p in base.iterdir() if p.is_dir() and re.fullmatch(r"\d{8}", p.name)]
        if len(candidates) <= keep:
            return []

        candidates.sort(key=lambda p: p.name, reverse=True)
        to_delete = candidates[keep:]
        deleted: List[str] = []
        for p in to_delete:
            shutil.rmtree(p, ignore_errors=True)
            deleted.append(p.name)
        return deleted

