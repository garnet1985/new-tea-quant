"""Opportunity CSV 读写格式工具。"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List


class OpportunityCsvHelper:
    """统一 opportunities CSV 格式（entity / slice 共用）。"""

    @staticmethod
    def write(
        output_dir: Path,
        stock_id: str,
        opportunities: List[Dict[str, Any]],
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_file = output_dir / f"{stock_id}_opportunities.csv"
        if not opportunities:
            csv_file.write_text("", encoding="utf-8")
            return csv_file

        fieldnames = list(opportunities[0].keys())
        with csv_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in opportunities:
                writer.writerow(row)
        return csv_file

    @staticmethod
    def collect_from_dir(source: Path) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        if not source.is_dir():
            return opportunities
        for entry in source.iterdir():
            if not entry.is_file() or not entry.name.endswith("_opportunities.csv"):
                continue
            stock_id = entry.name[: -len("_opportunities.csv")]
            with entry.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    payload = dict(row or {})
                    payload["stock_id"] = stock_id
                    opportunities.append(payload)
        return opportunities


__all__ = ["OpportunityCsvHelper"]
