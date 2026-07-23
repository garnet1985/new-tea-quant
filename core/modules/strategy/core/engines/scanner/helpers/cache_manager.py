"""扫描结果 CSV 缓存。"""

from __future__ import annotations

import csv
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.utils.io.csv_io import write_dicts_to_csv

logger = logging.getLogger(__name__)


@dataclass
class ScanCacheManager:
    strategy_name: str
    max_cache_days: int = 10

    def __post_init__(self) -> None:
        self.cache_base_dir = ProjectContext.path.get_strategy_scan_results_directory(
            self.strategy_name
        )
        self.cache_base_dir.mkdir(parents=True, exist_ok=True)

    def opportunities_csv_path(self, date: str) -> Path:
        return self.cache_base_dir / str(date).strip() / "opportunities.csv"

    def save_opportunities(self, date: str, opportunities: List[Opportunity]) -> None:
        if not opportunities:
            return
        day = str(date or "").strip()
        if not day:
            return
        date_dir = self.cache_base_dir / day
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
            write_dicts_to_csv(csv_path, rows, preferred_order=sorted(all_keys))

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
