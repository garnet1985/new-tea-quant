#!/usr/bin/env python3
from dataclasses import dataclass
from pathlib import Path
from typing import List
import csv
import logging

from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.infra.project_context import PathManager

logger = logging.getLogger(__name__)


@dataclass
class ScanCacheManager:
    strategy_name: str
    max_cache_days: int = 10

    def __post_init__(self):
        self.cache_base_dir = PathManager.strategy_scan_cache(self.strategy_name)
        self.cache_base_dir.mkdir(parents=True, exist_ok=True)

    def save_opportunities(self, date: str, opportunities: List[Opportunity]) -> None:
        if not opportunities:
            return
        date_dir = self.cache_base_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        csv_path = date_dir / "opportunities.csv"
        rows = []
        for opp in opportunities:
            row = opp.to_dict()
            for key, value in row.items():
                if value is None:
                    row[key] = ""
                elif isinstance(value, dict):
                    import json

                    row[key] = json.dumps(value, ensure_ascii=False, default=str)
                elif not isinstance(value, (str, int, float, bool)):
                    row[key] = str(value)
            rows.append(row)
        if rows:
            from core.utils.io.csv_io import write_dicts_to_csv

            all_keys = {k for row in rows for k in row.keys()}
            fieldnames = sorted(all_keys)
            write_dicts_to_csv(csv_path, rows, preferred_order=fieldnames)

    def load_opportunities(self, date: str) -> List[Opportunity]:
        csv_path = self.cache_base_dir / date / "opportunities.csv"
        if not csv_path.exists():
            return []
        opportunities = []
        try:
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for key, value in row.items():
                        if value and value.startswith("{"):
                            try:
                                import json

                                row[key] = json.loads(value)
                            except Exception:
                                pass
                    opportunities.append(Opportunity.from_dict(row))
        except Exception as exc:
            logger.warning("[ScanCacheManager] load failed: %s", exc)
        return opportunities

    def cleanup_old_cache(self) -> None:
        if not self.cache_base_dir.exists():
            return
        date_dirs = [d for d in self.cache_base_dir.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 8]
        if len(date_dirs) <= self.max_cache_days:
            return
        date_dirs.sort(key=lambda d: d.name, reverse=True)
        for date_dir in date_dirs[self.max_cache_days :]:
            try:
                import shutil

                shutil.rmtree(date_dir)
            except Exception as exc:
                logger.warning("[ScanCacheManager] cleanup failed: %s", exc)


__all__ = ["ScanCacheManager"]
