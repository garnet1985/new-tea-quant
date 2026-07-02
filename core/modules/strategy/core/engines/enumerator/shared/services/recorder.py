"""枚举输出记录器（有状态，主进程管理，不序列化到子进程）。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
from core.modules.strategy.core.engines.enumerator.entity_based.runtime_context.context import EntityBasedRuntimeContext

logger = logging.getLogger(__name__)


@dataclass
class EnumeratorOutputRecorder:
    """枚举输出记录器（有状态，主进程管理，不序列化到子进程）。

    生命周期：
    - Preprocess：创建recorder，保存执行元数据
    - Execute：通过callback记录opportunity
    - Postprocess：保存最终结果
    """

    # Context信息（初始化时保存）
    output_dir: Path
    strategy_id: str                # 策略ID（relative_path）
    version_id: int
    version_dir_name: str
    fingerprint_hash: str

    # 运行时状态（跨越三个阶段）
    fingerprint: Optional[Dict[str, Any]] = None
    jobs: Optional[List[Dict[str, Any]]] = None
    settings_diff: Optional[Dict[str, Any]] = None
    stock_opportunities: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    stock_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: EntityBasedRuntimeContext) -> EnumeratorOutputRecorder:
        """从context初始化recorder。"""
        return cls(
            output_dir=context.info.output_dir,
            strategy_id=context.info.strategy_id,
            version_id=context.info.version_id,
            version_dir_name=context.info.version_dir_name,
            fingerprint_hash=context.info.fingerprint_hash,
        )

    def save_execution_metadata(
        self,
        fingerprint: Dict[str, Any],
        total_jobs: int,
        jobs_sample: List[Dict[str, Any]],
        settings_diff: Dict[str, Any],
    ) -> None:
        """保存执行元数据（preprocess阶段，只保存元信息）。"""
        self.fingerprint = dict(fingerprint)
        self.settings_diff = dict(settings_diff)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        jobs_file = self.output_dir / "_jobs_metadata.json"
        try:
            with jobs_file.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "fingerprint_hash": self.fingerprint_hash,
                        "total_jobs": total_jobs,
                        "jobs_sample": jobs_sample,
                        "settings_diff": settings_diff,
                    },
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info("Saved execution metadata: total_jobs=%d", total_jobs)
        except Exception as exc:
            logger.warning("Failed to save execution metadata: %s", exc)

    def record_opportunity(
        self,
        stock_id: str,
        opportunities: List[Dict[str, Any]],
    ) -> None:
        """记录opportunity（execute阶段，通过callback）。"""
        self.stock_opportunities[stock_id] = list(opportunities)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            csv_file = OpportunityCsvHelper.write(self.output_dir, stock_id, opportunities)
            logger.info("Saved opportunities CSV: %s (%d rows)", csv_file, len(opportunities))
        except Exception as exc:
            logger.error("Failed to save opportunities CSV for %s: %s", stock_id, exc)

    def save_final_results(
        self,
        metadata: Dict[str, Any],
        report: Dict[str, Any],
        stock_summary: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """保存最终结果（postprocess阶段）。"""
        self.metadata = dict(metadata)
        self.report = dict(report)
        if stock_summary:
            self.stock_summary = dict(stock_summary)

        # 保存metadata.json
        metadata_file = self.output_dir / "_metadata.json"
        try:
            with metadata_file.open("w", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2, ensure_ascii=False)
            logger.info("Saved metadata: %s", metadata_file)
        except Exception as exc:
            logger.warning("Failed to save metadata: %s", exc)

        # 保存report.json
        report_file = self.output_dir / "_report.json"
        try:
            with report_file.open("w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False)
            logger.info("Saved report: %s", report_file)
        except Exception as exc:
            logger.warning("Failed to save report: %s", exc)


__all__ = ["EnumeratorOutputRecorder"]