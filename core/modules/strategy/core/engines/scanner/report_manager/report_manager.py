"""Scanner ReportManager — date-keyed cache + adapters。

生命周期: begin → collect → summarize → save → present / finalize
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from core.modules.strategy.core.engines.scanner.helpers import (
    AdapterDispatcher,
    ScanCacheManager,
)
from core.modules.strategy.core.engines.scanner.report_manager.scan_summary import (
    ScanSummary,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
)


@dataclass
class ReportManager(BaseReportManager):
    """扫描 run 产物编排。

    边界:
    - 负责: collect opportunities、summary、cache CSV、adapter present
    - 不负责: BE 调度 / 日期解析
    - 调用方: ScannerPipeline
    """

    strategy_key: str = ""
    scan_date: str = ""
    stock_ids: List[str] = field(default_factory=list)
    date_meta: Dict[str, Any] = field(default_factory=dict)
    adapter_names: List[str] = field(default_factory=list)
    max_cache_days: int = 10
    skip_save: bool = False
    opportunities: List[Opportunity] = field(default_factory=list)
    summary: Optional[ScanSummary] = field(default=None, init=False, repr=False)
    _cache: Optional[ScanCacheManager] = field(default=None, init=False, repr=False)

    @classmethod
    def begin(
        cls,
        *,
        strategy_key: str,
        scan_date: str,
        stock_ids: List[str],
        date_meta: Optional[Dict[str, Any]] = None,
        adapter_names: Optional[List[str]] = None,
        max_cache_days: int = 10,
        skip_save: bool = False,
    ) -> "ReportManager":
        key = str(strategy_key or "").strip()
        day = str(scan_date or "").strip()
        cache = ScanCacheManager(key, max_cache_days=int(max_cache_days))
        output_dir = cache.cache_base_dir / day if day else cache.cache_base_dir
        mgr = cls(
            output_dir=output_dir,
            strategy_key=key,
            scan_date=day,
            stock_ids=list(stock_ids or []),
            date_meta=dict(date_meta or {}),
            adapter_names=list(adapter_names or []),
            max_cache_days=int(max_cache_days),
            skip_save=bool(skip_save),
        )
        mgr._cache = cache
        return mgr

    def collect(self, item: Any) -> None:
        """接受 ``List[Opportunity]``、单条 Opportunity、或 BE ``run_result``。"""
        if item is None:
            return
        if isinstance(item, Opportunity):
            self.opportunities.append(item)
            return
        if isinstance(item, list):
            for row in item:
                self.collect(row)
            return
        for report in list(getattr(item, "job_results", None) or []):
            if not getattr(report, "success", False):
                continue
            data = report.data if isinstance(report.data, dict) else {}
            rows = data.get("opportunities") or []
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, dict):
                    self.opportunities.append(Opportunity.from_dict(row))
                elif isinstance(row, Opportunity):
                    self.opportunities.append(row)

    def summarize(self) -> ScanSummary:
        self.summary = ScanSummary.from_opportunities(self.opportunities)
        return self.summary

    def save(self) -> Optional[Path]:
        if self.skip_save or not self.opportunities:
            return None
        cache = self._cache or ScanCacheManager(
            self.strategy_key, max_cache_days=self.max_cache_days
        )
        cache.save_opportunities(self.scan_date, self.opportunities)
        path = cache.opportunities_csv_path(self.scan_date)
        return path if path.is_file() else None

    def present(self, stream: Optional[TextIO] = None) -> None:
        _ = stream
        summary = self.summary or self.summarize()
        AdapterDispatcher(self.strategy_key).dispatch(
            adapter_names=self.adapter_names,
            opportunities=self.opportunities,
            context={
                "date": self.scan_date,
                "strategy_name": self.strategy_key,
                "scan_summary": summary.to_dict(),
                "date_meta": dict(self.date_meta or {}),
            },
        )

    def finalize(self, *, present: bool = True, **kwargs: Any) -> Dict[str, Any]:
        _ = kwargs
        summary = self.summarize()
        self.save()
        if present:
            self.present()
        return {
            "date": self.scan_date,
            "total_opportunities": len(self.opportunities),
            "total_stocks": len(self.stock_ids),
            "summary": summary.to_dict(),
            "date_meta": dict(self.date_meta or {}),
        }


__all__ = ["ReportManager"]
