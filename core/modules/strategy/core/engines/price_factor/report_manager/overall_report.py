"""价格回测 overall_report.json —— CMD / UI / DB 同一契约。"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, TYPE_CHECKING

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    OVERALL_REPORT_FILE,
)
from core.modules.strategy.core.engines.price_factor.report_manager.price_metrics import (
    RoiDistribution,
    SkipCounters,
)
from core.modules.strategy.core.engines.price_factor.report_manager.report_scan import (
    PriceCsvScan,
)


@dataclass
class OverallSummary:
    """价格回测总体指标（磁盘 snake_case；对齐 UI 各区块）。"""

    win_rate: float = 0.0
    avg_roi: float = 0.0
    annual_return: float = 0.0
    annual_return_in_trading_days: float = 0.0
    avg_duration_in_days: float = 0.0
    avg_duration_in_trading_days: float = 0.0
    total_investments: int = 0
    total_open_investments: int = 0
    total_win_investments: int = 0
    total_loss_investments: int = 0
    total_completed_investments: int = 0
    total_unfinished_investments: int = 0
    completion_rate: float = 0.0
    total_profit: float = 0.0
    avg_profit_per_investment: float = 0.0
    avg_profit_per_stock: float = 0.0
    avg_investments_per_stock: float = 0.0
    stocks_have_opportunities: int = 0
    skips: SkipCounters = field(default_factory=SkipCounters)
    roi: RoiDistribution = field(default_factory=RoiDistribution)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "win_rate": self.win_rate,
            "avg_roi": self.avg_roi,
            "annual_return": self.annual_return,
            "annual_return_in_trading_days": self.annual_return_in_trading_days,
            "avg_duration_in_days": self.avg_duration_in_days,
            "avg_duration_in_trading_days": self.avg_duration_in_trading_days,
            "total_investments": self.total_investments,
            "total_open_investments": self.total_open_investments,
            "total_win_investments": self.total_win_investments,
            "total_loss_investments": self.total_loss_investments,
            "total_completed_investments": self.total_completed_investments,
            "total_unfinished_investments": self.total_unfinished_investments,
            "completion_rate": self.completion_rate,
            "total_profit": self.total_profit,
            "avg_profit_per_investment": self.avg_profit_per_investment,
            "avg_profit_per_stock": self.avg_profit_per_stock,
            "avg_investments_per_stock": self.avg_investments_per_stock,
            "stocks_have_opportunities": self.stocks_have_opportunities,
        }
        payload.update(self.skips.to_dict())
        payload.update(self.roi.to_dict())
        return payload

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OverallSummary":
        data = raw or {}
        return cls(
            win_rate=float(data.get("win_rate") or 0.0),
            avg_roi=float(data.get("avg_roi") or 0.0),
            annual_return=float(data.get("annual_return") or 0.0),
            annual_return_in_trading_days=float(
                data.get("annual_return_in_trading_days") or 0.0
            ),
            avg_duration_in_days=float(data.get("avg_duration_in_days") or 0.0),
            avg_duration_in_trading_days=float(
                data.get("avg_duration_in_trading_days") or 0.0
            ),
            total_investments=int(data.get("total_investments") or 0),
            total_open_investments=int(data.get("total_open_investments") or 0),
            total_win_investments=int(data.get("total_win_investments") or 0),
            total_loss_investments=int(data.get("total_loss_investments") or 0),
            total_completed_investments=int(
                data.get("total_completed_investments") or 0
            ),
            total_unfinished_investments=int(
                data.get("total_unfinished_investments") or 0
            ),
            completion_rate=float(data.get("completion_rate") or 0.0),
            total_profit=float(data.get("total_profit") or 0.0),
            avg_profit_per_investment=float(
                data.get("avg_profit_per_investment") or 0.0
            ),
            avg_profit_per_stock=float(data.get("avg_profit_per_stock") or 0.0),
            avg_investments_per_stock=float(
                data.get("avg_investments_per_stock") or 0.0
            ),
            stocks_have_opportunities=int(data.get("stocks_have_opportunities") or 0),
            skips=SkipCounters.from_dict(data),
            roi=RoiDistribution.from_dict(data),
        )

    @classmethod
    def build_from_scan(cls, scan: PriceCsvScan) -> "OverallSummary":
        investments = scan.all_investments
        total = 0
        win = 0
        loss = 0
        open_n = 0
        roi_sum = 0.0
        roi_n = 0
        hold_sum = 0.0
        hold_n = 0
        profit_sum = 0.0
        with_inv = 0

        for rows in scan.investments_by_entity.values():
            if not rows:
                continue
            with_inv += 1
            for row in rows:
                if row.skip_reason:
                    continue
                total += 1
                result = (row.result or "").strip().lower()
                lifecycle = (row.lifecycle or "").strip().lower()
                if result in {"win", "profit"} or (row.roi > 0 and row.exit_date):
                    win += 1
                elif result in {"loss"} or (row.roi < 0 and row.exit_date):
                    loss += 1
                elif not row.exit_date or lifecycle in {"open", "holding", "active"}:
                    open_n += 1

                if row.exit_date or row.roi != 0.0:
                    roi_sum += float(row.roi)
                    roi_n += 1
                if row.holding_days:
                    hold_sum += float(row.holding_days)
                    hold_n += 1
                enter_px = float(row.enter_price or 0.0)
                if enter_px != 0.0:
                    profit_sum += float(row.roi) * enter_px

        completed = win + loss
        unfinished = open_n
        avg_roi = (roi_sum / float(roi_n)) if roi_n else 0.0
        avg_duration = (hold_sum / float(hold_n)) if hold_n else 0.0
        avg_duration_td = (
            avg_duration * (250.0 / 365.0) if avg_duration > 0 else 0.0
        )
        annual = (
            avg_roi * (365.0 / avg_duration) if avg_duration > 0 else 0.0
        )
        annual_td = (
            avg_roi * (250.0 / avg_duration) if avg_duration > 0 else 0.0
        )
        return cls(
            win_rate=round((float(win) / float(total) * 100.0), 1) if total else 0.0,
            avg_roi=round(avg_roi, 4),
            annual_return=round(annual, 4),
            annual_return_in_trading_days=round(annual_td, 4),
            avg_duration_in_days=round(avg_duration, 1),
            avg_duration_in_trading_days=round(avg_duration_td, 1),
            total_investments=total,
            total_open_investments=open_n,
            total_win_investments=win,
            total_loss_investments=loss,
            total_completed_investments=completed,
            total_unfinished_investments=unfinished,
            completion_rate=round((float(completed) / float(total)), 4) if total else 0.0,
            total_profit=round(profit_sum, 2),
            avg_profit_per_investment=round(profit_sum / float(total), 2) if total else 0.0,
            avg_profit_per_stock=round(profit_sum / float(with_inv), 2) if with_inv else 0.0,
            avg_investments_per_stock=round(float(total) / float(with_inv), 2)
            if with_inv
            else 0.0,
            stocks_have_opportunities=with_inv,
            skips=SkipCounters.compute(investments),
            roi=RoiDistribution.compute(investments),
        )


@dataclass
class OverallReport:
    """价格总体报告稿（文件 / DB / presenter 同一契约）。"""

    OVERALL_REPORT_FILE = OVERALL_REPORT_FILE

    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    enum_version_id: str = ""
    backtest_period: Dict[str, str] = field(default_factory=dict)
    summary: OverallSummary = field(default_factory=OverallSummary)
    created_at: str = ""

    @classmethod
    def build_from_scan(cls, scan: PriceCsvScan) -> "OverallReport":
        return cls(
            strategy_key=scan.strategy_key,
            strategy_path=scan.strategy_path,
            version_id=scan.version_id,
            enum_version_id=scan.enum_version_id,
            backtest_period=dict(scan.backtest_period or {}),
            summary=OverallSummary.build_from_scan(scan),
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def build(
        cls,
        output_dir: Path,
        *,
        entity_ids: Optional[List[str]] = None,
        strategy_key: str = "",
        version_id: int = 0,
    ) -> "OverallReport":
        scan = PriceCsvScan.collect(
            output_dir,
            entity_ids=entity_ids,
            strategy_key=strategy_key,
            version_id=version_id,
        )
        return cls.build_from_scan(scan)

    @classmethod
    def load(cls, output_dir: Path) -> "OverallReport":
        path = Path(output_dir) / cls.OVERALL_REPORT_FILE
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, output_dir: Path) -> Path:
        path = Path(output_dir) / self.OVERALL_REPORT_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        s = self.summary
        period = self.backtest_period or {}

        CmdLayout.title.print_banner(f"{icon('line_chart')} 价格回测报告", stream=out)
        print(
            f"{icon('gear')} {self.strategy_key} v{self.version_id}  "
            f"{icon('calendar')} {period.get('start_date', '')}~{period.get('end_date', '')}",
            file=out,
            flush=True,
        )
        print(f"   path={self.strategy_path or '-'}", file=out, flush=True)

        CmdLayout.separator.print_line(width=60, stream=out)
        CmdLayout.title.print_section(f"{icon('target')} 回测总体", stream=out)
        wr_icon = icon("success") if s.win_rate >= 50.0 else icon("warning")
        roi_icon = icon("line_chart") if s.avg_roi >= 0 else icon("downward_trend")
        print(
            f"{wr_icon} 胜率 {s.win_rate:.1f}%    "
            f"{roi_icon} 均ROI {s.avg_roi * 100:.2f}%    "
            f"{icon('clock')} 均持有 {s.avg_duration_in_days:.1f}天    "
            f"年化 {s.annual_return * 100:.1f}%",
            file=out,
            flush=True,
        )

        CmdLayout.title.print_section(f"{icon('search')} 样本与覆盖", stream=out)
        print(
            f"投资 {s.total_investments} · 有仓股票 {s.stocks_have_opportunities} · "
            f"均每股 {s.avg_investments_per_stock:.2f} · 未平 {s.total_open_investments}",
            file=out,
            flush=True,
        )

        CmdLayout.title.print_section(f"{icon('bar_chart')} 盈亏结构", stream=out)
        if s.total_win_investments or s.total_loss_investments:
            CmdLayout.bar_chart.print(
                [("win", s.total_win_investments), ("loss", s.total_loss_investments)],
                title=f"{icon('bar_chart')} 胜负",
                width=24,
                stream=out,
            )
        print(
            f"均利/笔 {s.avg_profit_per_investment:.2f} · 均利/股 {s.avg_profit_per_stock:.2f}",
            file=out,
            flush=True,
        )

        skips = s.skips
        CmdLayout.title.print_section(f"{icon('warning')} 成交跳过", stream=out)
        print(
            f"涨停无法买 {skips.skipped_buy_at_limit_up} · "
            f"跌停无法卖 {skips.skipped_sell_at_limit_down} · "
            f"状态跳过 {skips.skipped_stock_status}",
            file=out,
            flush=True,
        )

        roi = s.roi
        if roi.roi_percentile_values:
            CmdLayout.title.print_section(f"{icon('chart')} ROI 分布", stream=out)
            print(
                f"样本 {roi.roi_distribution_sample_count} · "
                f"强平剔除 {roi.roi_truncated_exit_count} · "
                f"SD {roi.roi_std_pct}% · {roi.roi_conclusion or '—'}",
                file=out,
                flush=True,
            )
            # 分位可为负；BarChart 会钳成 0，且占比列对分位无意义 → 直接打印带符号数值
            print(f"{icon('chart')} ROI 分位", file=out, flush=True)
            labels = list(roi.roi_percentile_labels or [])
            values = list(roi.roi_percentile_values or [])
            label_w = max((len(str(lb)) for lb in labels), default=6)
            label_w = max(label_w, len("分位"))
            print(f"  {'分位':<{label_w}}      ROI", file=out, flush=True)
            for label, value in zip(labels, values):
                print(
                    f"  {str(label):<{label_w}}  {float(value):+7.2f}%",
                    file=out,
                    flush=True,
                )
            if roi.roi_bucket_labels and roi.roi_bucket_counts:
                CmdLayout.bar_chart.print(
                    list(zip(roi.roi_bucket_labels, roi.roi_bucket_counts)),
                    title=f"{icon('bar_chart')} ROI 分桶",
                    width=24,
                    skip_empty=True,
                    headers=("区间", "分布", "笔数", "占比"),
                    stream=out,
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "version_id": self.version_id,
            "enum_version_id": self.enum_version_id,
            "backtest_period": dict(self.backtest_period or {}),
            "summary": self.summary.to_dict(),
            "created_at": self.created_at,
        }

    def to_ui_dict(self) -> Dict[str, Any]:
        """UI / DB：``priceMetrics`` camelCase + backtest_period。"""
        s = self.summary
        sk = s.skips
        r = s.roi
        out: Dict[str, Any] = {
            "priceMetrics": {
                "winRate": s.win_rate,
                "avgRoi": round(s.avg_roi * 100.0, 2) if abs(s.avg_roi) < 1 else s.avg_roi,
                "avgDurationDays": s.avg_duration_in_days,
                "annualReturn": round(s.annual_return * 100.0, 2),
                "totalInvestments": s.total_investments,
                "totalOpenInvestments": s.total_open_investments,
                "totalWinInvestments": s.total_win_investments,
                "totalLossInvestments": s.total_loss_investments,
                "stocksHaveOpportunities": s.stocks_have_opportunities,
                "avgInvestmentsPerStock": s.avg_investments_per_stock,
                "avgProfitPerInvestment": s.avg_profit_per_investment,
                "avgProfitPerStock": s.avg_profit_per_stock,
                "skippedBuyAtLimitUp": sk.skipped_buy_at_limit_up,
                "skippedSellAtLimitDown": sk.skipped_sell_at_limit_down,
                "skippedStockStatus": sk.skipped_stock_status,
                "roiPercentileLabels": list(r.roi_percentile_labels),
                "roiPercentileValues": list(r.roi_percentile_values),
                "roiP10": r.roi_p10,
                "roiP20": r.roi_p20,
                "roiP30": r.roi_p30,
                "roiP40": r.roi_p40,
                "roiP50": r.roi_p50,
                "roiP60": r.roi_p60,
                "roiP70": r.roi_p70,
                "roiP80": r.roi_p80,
                "roiP90": r.roi_p90,
                "roiP25": r.roi_p25,
                "roiP75": r.roi_p75,
                "roiIqr": r.roi_iqr,
                "roiStdPct": r.roi_std_pct,
                "roiConclusion": r.roi_conclusion,
                "roiBucketLabels": list(r.roi_bucket_labels),
                "roiBucketCounts": list(r.roi_bucket_counts),
                "roiBucketBinCount": r.roi_bucket_bin_count,
                "roiTruncatedExitCount": r.roi_truncated_exit_count,
                "roiDistributionSampleCount": r.roi_distribution_sample_count,
            },
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "version_id": self.version_id,
            "enum_version_id": self.enum_version_id,
            "output_dir": "",
        }
        if self.backtest_period.get("start_date") and self.backtest_period.get("end_date"):
            out["backtest_period"] = dict(self.backtest_period)
        return out

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OverallReport":
        data = raw or {}
        summary_raw = data.get("summary")
        if not isinstance(summary_raw, dict):
            raise ValueError("overall_report 缺少 summary 对象")
        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            strategy_path=str(data.get("strategy_path") or ""),
            version_id=int(data.get("version_id") or 0),
            enum_version_id=str(data.get("enum_version_id") or ""),
            backtest_period=dict(data.get("backtest_period") or {}),
            summary=OverallSummary.from_dict(summary_raw),
            created_at=str(data.get("created_at") or ""),
        )


class OverallReportHandle:
    """ReportManager.overall 门面。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager
        self._report: Optional[OverallReport] = None

    def build_from_scan(self, scan: PriceCsvScan) -> "OverallReportHandle":
        self._report = OverallReport.build_from_scan(scan)
        return self

    def build(self) -> "OverallReportHandle":
        self._report = OverallReport.build(
            self._manager.output_dir,
            entity_ids=list(self._manager.entity_ids),
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
        )
        return self

    def save(self) -> Path:
        if self._report is None:
            self.build()
        assert self._report is not None
        return self._report.save(self._manager.output_dir)

    def load(self) -> Dict[str, Any]:
        return OverallReport.load(self._manager.output_dir).to_dict()

    def present(self, stream: Optional[TextIO] = None) -> None:
        OverallReport.load(self._manager.output_dir).present(stream=stream)

    @property
    def report(self) -> Optional[OverallReport]:
        return self._report


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.price_factor.report_manager.report_manager import (
        ReportManager,
    )


__all__ = [
    "OverallSummary",
    "OverallReport",
    "OverallReportHandle",
]
