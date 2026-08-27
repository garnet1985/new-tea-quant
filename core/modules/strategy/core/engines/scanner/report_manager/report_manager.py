"""Scanner ReportManager — date-keyed 摘要 + opportunities CSV。

产物（``results/scan/{YYYYMMDD}/``）:
- scan_summary.json  — 全局摘要（CMD / 返回值同源）
- opportunities.csv  — 机会明细（有机会时）

读写走 ``ArtifactStore.scan_at`` / ``ScanStore``；不进仿真 version。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.engines.scanner.helpers import AdapterDispatcher
from core.modules.strategy.core.engines.scanner.report_manager.scan_summary import (
    ScanSummary,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
)
from core.modules.strategy.core.services.artifacts.consts import (
    SCAN_OPPORTUNITIES_FILE,
    SCAN_SUMMARY_FILE,
)
from core.modules.strategy.core.services.artifacts.scan_store import ScanStore
from core.modules.strategy.core.services.artifacts.store import ArtifactStore

OPPORTUNITIES_CSV_FILE = SCAN_OPPORTUNITIES_FILE


@dataclass
class ReportManager(BaseReportManager):
    """扫描 run 产物编排。

    边界:
    - 负责: collect opportunities、summary、落盘、adapter present
    - 不负责: BE 调度 / 日期解析 / 磁盘路径
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
    _store: Optional[ScanStore] = field(default=None, init=False, repr=False)

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
        strategy_folder: Optional[Path] = None,
    ) -> "ReportManager":
        key = str(strategy_key or "").strip()
        day = str(scan_date or "").strip()
        root = strategy_folder if strategy_folder is not None else key
        store = ArtifactStore.scan_at(root, day) if day else None
        output_dir = store.output_dir if store is not None else Path()
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
        mgr._store = store
        return mgr

    @staticmethod
    def load_opportunities(store: ScanStore) -> List[Opportunity]:
        return [Opportunity.from_dict(row) for row in store.read_opportunity_rows()]

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

    def to_report_dict(self) -> Dict[str, Any]:
        """CMD / Scan 页 / 落盘共用的报告字典。"""
        summary = self.summary or self.summarize()
        return {
            "strategy_key": self.strategy_key,
            "date": self.scan_date,
            "total_opportunities": len(self.opportunities),
            "total_stocks": len(self.stock_ids),
            "summary": summary.to_dict(),
            "date_meta": dict(self.date_meta or {}),
        }

    def to_ui_dict(self) -> Dict[str, Any]:
        """Scan 页消费的 camelCase 摘要（明细仍走 opportunities 列表 / CSV）。"""
        summary = self.summary or self.summarize()
        return {
            "scanMetrics": {
                "date": self.scan_date,
                "totalOpportunities": len(self.opportunities),
                "totalStocksScanned": len(self.stock_ids),
                "hitStocks": summary.total_stocks,
                "atLimitUpCount": summary.at_limit_up_count,
            },
            "strategy_key": self.strategy_key,
            "date": self.scan_date,
            "summary": summary.to_dict(),
            "date_meta": dict(self.date_meta or {}),
        }

    def save(self) -> Optional[Path]:
        if self.skip_save:
            return None
        if not self.scan_date:
            return None
        store = self._store or ArtifactStore.scan_at(self.strategy_key, self.scan_date)
        summary_path = store.write_summary(self.to_report_dict())
        store.write_opportunity_rows([opp.to_dict() for opp in self.opportunities])
        return summary_path

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        report = self.to_report_dict()
        summary = report["summary"]
        CmdLayout.title.print_banner(f"{icon('search')} 扫描报告", stream=out)
        print(
            f"{icon('calendar')} {report['date']}  "
            f"{icon('gear')} {self.strategy_key}",
            file=out,
            flush=True,
        )
        print(
            f"{icon('green_dot')} 机会 {report['total_opportunities']}  "
            f"宇宙 {report['total_stocks']}  "
            f"命中股 {summary.get('total_stocks', 0)}  "
            f"涨停入场 {summary.get('at_limit_up_count', 0)}",
            file=out,
            flush=True,
        )
        print(f"{icon('info')} 产物: {self.output_dir}", file=out, flush=True)
        print(
            f"   files: {SCAN_SUMMARY_FILE}"
            + (f", {OPPORTUNITIES_CSV_FILE}" if self.opportunities else ""),
            file=out,
            flush=True,
        )

        AdapterDispatcher(self.strategy_key).dispatch(
            adapter_names=self.adapter_names,
            opportunities=self.opportunities,
            context={
                "date": self.scan_date,
                "strategy_name": self.strategy_key,
                "scan_summary": summary,
                "date_meta": dict(self.date_meta or {}),
            },
        )

    def finalize(self, *, present: bool = True, **kwargs: Any) -> Dict[str, Any]:
        _ = kwargs
        self.summarize()
        self.save()
        if present:
            self.present()
        return self.to_report_dict()


__all__ = [
    "OPPORTUNITIES_CSV_FILE",
    "ReportManager",
    "SCAN_SUMMARY_FILE",
]
