"""枚举中间结果持久化（preprocess / execute / postprocess）。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper

logger = logging.getLogger(__name__)


@dataclass
class EnumeratorOutputRecorder:
    """枚举 run 三阶段磁盘输出。"""

    output_dir: Path
    strategy_name: str
    version_id: int
    version_dir_name: str

    fingerprint: Optional[Dict[str, Any]] = None
    jobs: Optional[List[Dict[str, Any]]] = None
    settings_diff: Optional[Dict[str, Any]] = None
    stock_opportunities: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    stock_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def save_preprocess_intermediate(
        self,
        fingerprint: Dict[str, Any],
        jobs: List[Dict[str, Any]],
        settings_diff: Dict[str, Any],
    ) -> None:
        self.fingerprint = dict(fingerprint)
        self.jobs = list(jobs)
        self.settings_diff = dict(settings_diff)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        jobs_file = self.output_dir / "_jobs_metadata.json"
        try:
            with jobs_file.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "total_jobs": len(jobs),
                        "jobs_sample": jobs[:3] if len(jobs) > 3 else jobs,
                    },
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info("Saved jobs metadata: %s", jobs_file)
        except Exception as exc:
            logger.warning("Failed to save jobs metadata: %s", exc)

    def save_stock_opportunities(
        self,
        stock_id: str,
        opportunities: List[Dict[str, Any]],
    ) -> None:
        self.stock_opportunities[stock_id] = list(opportunities)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            csv_file = OpportunityCsvHelper.write(self.output_dir, stock_id, opportunities)
            logger.info("Saved opportunities CSV: %s (%d rows)", csv_file, len(opportunities))
        except Exception as exc:
            logger.error("Failed to save opportunities CSV for %s: %s", stock_id, exc)

    def save_postprocess_intermediate(
        self,
        metadata: Dict[str, Any],
        report: Dict[str, Any],
        stock_summary: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.metadata = dict(metadata)
        self.report = dict(report)
        if stock_summary:
            self.stock_summary = dict(stock_summary)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        metadata_file = self.output_dir / "0_metadata.json"
        try:
            with metadata_file.open("w", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2, ensure_ascii=False)
            logger.info("Saved metadata: %s", metadata_file)
        except Exception as exc:
            logger.error("Failed to save metadata: %s", exc)

        report_file = self.output_dir / "0_report_enum.json"
        try:
            with report_file.open("w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False)
            logger.info("Saved report: %s", report_file)
        except Exception as exc:
            logger.error("Failed to save report: %s", exc)

        if stock_summary:
            summary_file = self.output_dir / "0_stock_summary.json"
            try:
                with summary_file.open("w", encoding="utf-8") as handle:
                    json.dump(stock_summary, handle, indent=2, ensure_ascii=False)
                logger.info("Saved stock_summary: %s", summary_file)
            except Exception as exc:
                logger.warning("Failed to save stock_summary: %s", exc)


__all__ = ["EnumeratorOutputRecorder"]
