"""扫描结果按日 CSV 文件缓存（非 DB 工作台）。

本文件:
- ScanCacheManager: ``scan_results/{strategy}/{date}/opportunities.csv`` 读写与过期清理
  边界: 负责磁盘 scan 缓存；不负责 SimulationCacheManager 或 enum 产物
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.infra.utils import Utils

logger = logging.getLogger(__name__)


@dataclass
class ScanCacheManager:
    """Scan result cache under ``{strategy_root}/results/scan/``.

    ``strategy_root`` must be the discovered strategy folder (absolute Path preferred).
    Relative strings still resolve under ``userspace/strategies/`` for bootstrap.

    ``max_cache_days``：保留的日期版本数上限。``None`` 时读
    ``data.json`` ``retention.scan_results_max_versions``（缺则报错）。
    """

    strategy_root: Union[str, Path]
    max_cache_days: Optional[int] = None

    def __post_init__(self) -> None:
        if self.max_cache_days is None:
            self.max_cache_days = (
                ProjectContext.config.get_scan_results_max_versions()
            )
        else:
            value = int(self.max_cache_days)
            if value < 1:
                raise ValueError(f"max_cache_days 必须 >= 1，收到: {value}")
            self.max_cache_days = value
        self.cache_base_dir = ProjectContext.path.get_strategy_scan_results_directory(
            self.strategy_root
        )
        self.cache_base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def strategy_name(self) -> str:
        """Legacy alias (relative name or folder name) for logs / progress keys."""
        root = Path(self.strategy_root)
        return root.name if root.is_absolute() else str(self.strategy_root)

    def date_dir(self, date: str) -> Path:
        return self.cache_base_dir / str(date).strip()

    def opportunities_csv_path(self, date: str) -> Path:
        return self.date_dir(date) / "opportunities.csv"

    def scan_summary_path(self, date: str) -> Path:
        return self.date_dir(date) / "scan_summary.json"

    def save_scan_summary(self, date: str, payload: dict) -> Path:
        """写入 ``scan_summary.json``（即使 0 机会也落盘）。"""
        day = str(date or "").strip()
        if not day:
            raise ValueError("scan date 不能为空")
        date_dir = self.date_dir(day)
        date_dir.mkdir(parents=True, exist_ok=True)
        path = date_dir / "scan_summary.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def save_opportunities(self, date: str, opportunities: List[Opportunity]) -> None:
        day = str(date or "").strip()
        if not day:
            return
        # 0 机会：删除陈旧 CSV，避免 readiness 误读上一轮全量结果
        if not opportunities:
            csv_path = self.opportunities_csv_path(day)
            if csv_path.is_file():
                try:
                    csv_path.unlink()
                except OSError as exc:
                    logger.warning("删除空扫描 opportunities.csv 失败: %s", exc)
            return
        date_dir = self.date_dir(day)
        date_dir.mkdir(parents=True, exist_ok=True)
        csv_path = date_dir / "opportunities.csv"
        rows = []
        for opp in opportunities:
            row = opp.to_dict()
            for key, value in list(row.items()):
                if value is None:
                    row[key] = ""
                elif isinstance(value, dict):
                    row[key] = json.dumps(value, ensure_ascii=False, default=str)
                elif not isinstance(value, (str, int, float, bool)):
                    row[key] = str(value)
            rows.append(row)
        if rows:
            all_keys = {k for row in rows for k in row.keys()}
            Utils.io.write_dicts_to_csv(csv_path, rows, preferred_order=sorted(all_keys))

    def load_scan_summary(self, date: str) -> Optional[dict]:
        path = self.scan_summary_path(date)
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("读取 scan_summary 失败 date=%s: %s", date, exc)
            return None
        return raw if isinstance(raw, dict) else None

    def load_opportunities(self, date: str) -> List[Opportunity]:
        csv_path = self.opportunities_csv_path(date)
        if not csv_path.is_file():
            return []
        out: List[Opportunity] = []
        try:
            with csv_path.open("r", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    for key, value in list(row.items()):
                        if value and str(value).startswith("{"):
                            try:
                                row[key] = json.loads(value)
                            except Exception:
                                pass
                    out.append(Opportunity.from_dict(row))
        except Exception as exc:
            logger.warning("[ScanCacheManager] load failed: %s", exc)
        return out

    def cleanup_old_cache(self) -> None:
        if not self.cache_base_dir.exists():
            return
        date_dirs = [
            d
            for d in self.cache_base_dir.iterdir()
            if d.is_dir() and d.name.isdigit() and len(d.name) == 8
        ]
        if len(date_dirs) <= self.max_cache_days:
            return
        date_dirs.sort(key=lambda d: d.name, reverse=True)
        for date_dir in date_dirs[self.max_cache_days :]:
            try:
                shutil.rmtree(date_dir)
            except Exception as exc:
                logger.warning("[ScanCacheManager] cleanup failed: %s", exc)


__all__ = ["ScanCacheManager"]
