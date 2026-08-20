"""Portfolio overall_report.json —— CMD / UI / DB 同一契约。"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, TYPE_CHECKING

from core.infra.cmd_layout import CmdLayout
from core.modules.strategy.core.services.artifacts import (
    OVERALL_REPORT_FILE,
)
from core.modules.strategy.core.engines.portfolio.report_manager.capital_metrics import (
    EquityCurves,
    SkipMetrics,
    TradeQualityMetrics,
)


@dataclass
class OverallSummary:
    """资金总体指标（磁盘 snake_case；对齐 UI capital 区块）。"""

    initial_capital: float = 0.0
    final_cash: float = 0.0
    final_total_equity: float = 0.0
    total_return: float = 0.0
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    completed_investments: int = 0
    open_positions: int = 0
    win_rate: float = 0.0
    calmar_ratio: float = 0.0
    curves: EquityCurves = field(default_factory=EquityCurves)
    quality: TradeQualityMetrics = field(default_factory=TradeQualityMetrics)
    skips: SkipMetrics = field(default_factory=SkipMetrics)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "initial_capital": self.initial_capital,
            "final_cash": self.final_cash,
            "final_total_equity": self.final_total_equity,
            "total_return": self.total_return,
            "total_trades": self.total_trades,
            "buy_trades": self.buy_trades,
            "sell_trades": self.sell_trades,
            "completed_investments": self.completed_investments,
            "open_positions": self.open_positions,
            "win_rate": self.win_rate,
            "calmar_ratio": self.calmar_ratio,
        }
        payload.update(self.curves.to_dict())
        payload.update(self.quality.to_dict())
        payload.update(self.skips.to_dict())
        return payload

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "OverallSummary":
        data = raw or {}
        return cls(
            initial_capital=float(data.get("initial_capital") or 0.0),
            final_cash=float(data.get("final_cash") or 0.0),
            final_total_equity=float(data.get("final_total_equity") or 0.0),
            total_return=float(data.get("total_return") or 0.0),
            total_trades=int(data.get("total_trades") or 0),
            buy_trades=int(data.get("buy_trades") or 0),
            sell_trades=int(data.get("sell_trades") or 0),
            completed_investments=int(data.get("completed_investments") or 0),
            open_positions=int(data.get("open_positions") or 0),
            win_rate=float(data.get("win_rate") or 0.0),
            calmar_ratio=float(data.get("calmar_ratio") or 0.0),
            curves=EquityCurves.from_dict(data),
            quality=TradeQualityMetrics.from_dict(data),
            skips=SkipMetrics.from_dict(data),
        )

    @classmethod
    def build_from_sim(cls, sim: Any) -> "OverallSummary":
        account = sim.account
        initial = float(account.initial_cash)
        final_equity = float(account.equity({}))
        total_return = (final_equity / initial - 1.0) if initial > 0 else 0.0
        buy_n = sum(1 for t in sim.trades if t.is_buy())
        sell_n = sum(1 for t in sim.trades if t.is_sell())
        completed = int(sim.completed_count)
        win_rate = (
            (float(sim.win_count) / float(completed)) if completed > 0 else 0.0
        )

        per_profit: Dict[str, float] = {}
        per_sells: Dict[str, int] = {}
        for t in sim.trades:
            if not t.is_sell():
                continue
            eid = str(t.entity_id or "").strip()
            if not eid:
                continue
            per_profit[eid] = per_profit.get(eid, 0.0) + float(t.profit or 0.0)
            per_sells[eid] = per_sells.get(eid, 0) + 1

        curves = EquityCurves.compute(
            list(sim.equity_curve or []),
            initial_capital=initial,
        )
        quality = TradeQualityMetrics.compute(
            list(sim.trades or []),
            per_entity_profit=per_profit,
            per_entity_sells=per_sells,
        )
        mdd = float(curves.max_drawdown or 0.0)
        calmar = (total_return / mdd) if mdd > 1e-12 else 0.0
        return cls(
            initial_capital=initial,
            final_cash=float(account.cash),
            final_total_equity=final_equity,
            total_return=round(total_return, 6),
            total_trades=len(sim.trades),
            buy_trades=buy_n,
            sell_trades=sell_n,
            completed_investments=completed,
            open_positions=int(account.open_position_count()),
            win_rate=round(win_rate, 6),
            calmar_ratio=round(calmar, 4),
            curves=curves,
            quality=quality,
            skips=SkipMetrics.from_sim(sim),
        )


@dataclass
class OverallReport:
    """资金总体报告稿。"""

    OVERALL_REPORT_FILE = OVERALL_REPORT_FILE

    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    enum_version_id: str = ""
    backtest_period: Dict[str, str] = field(default_factory=dict)
    summary: OverallSummary = field(default_factory=OverallSummary)
    created_at: str = ""

    @classmethod
    def build_from_sim(
        cls,
        sim: Any,
        *,
        strategy_key: str = "",
        strategy_path: str = "",
        version_id: int = 0,
        enum_version_id: str = "",
        backtest_period: Optional[Dict[str, str]] = None,
    ) -> "OverallReport":
        return cls(
            strategy_key=strategy_key,
            strategy_path=strategy_path,
            version_id=version_id,
            enum_version_id=enum_version_id,
            backtest_period=dict(backtest_period or {}),
            summary=OverallSummary.build_from_sim(sim),
            created_at=datetime.now().isoformat(),
        )

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
        q = s.quality
        period = self.backtest_period or {}

        CmdLayout.title.print_banner(f"{icon('money')} 投资组合报告", stream=out)
        print(
            f"{icon('gear')} {self.strategy_key} v{self.version_id}  "
            f"{icon('calendar')} {period.get('start_date', '')}~{period.get('end_date', '')}",
            file=out,
            flush=True,
        )
        print(f"   path={self.strategy_path or '-'}", file=out, flush=True)

        CmdLayout.separator.print_line(width=60, stream=out)
        CmdLayout.title.print_section(f"{icon('target')} 资金结果", stream=out)
        ret_icon = icon("line_chart") if s.total_return >= 0 else icon("downward_trend")
        wr_pct = s.win_rate * 100.0 if abs(s.win_rate) <= 1 else s.win_rate
        print(
            f"{ret_icon} {s.initial_capital:.2f} → {s.final_total_equity:.2f}  "
            f"收益 {s.total_return * 100:.2f}%    "
            f"{icon('money')} 已实现 {q.total_profit:.2f}",
            file=out,
            flush=True,
        )
        print(
            f"{icon('success') if wr_pct >= 50 else icon('warning')} 胜率 {wr_pct:.1f}%    "
            f"完成 {s.completed_investments}    持仓 {s.open_positions}    "
            f"回撤 {s.curves.max_drawdown * 100:.2f}%    Calmar {s.calmar_ratio:.2f}",
            file=out,
            flush=True,
        )

        if q.win_trades or q.loss_trades:
            CmdLayout.bar_chart.print(
                [("win", q.win_trades), ("loss", q.loss_trades)],
                title=f"{icon('bar_chart')} 胜负",
                width=24,
                headers=("结果", "分布", "笔数", "占比"),
                stream=out,
            )
        if s.buy_trades or s.sell_trades:
            CmdLayout.bar_chart.print(
                [("buy", s.buy_trades), ("sell", s.sell_trades)],
                title=f"{icon('ongoing')} 买卖笔数",
                width=24,
                headers=("方向", "分布", "笔数", "占比"),
                stream=out,
            )

        sk = s.skips
        CmdLayout.title.print_section(f"{icon('warning')} 成交跳过", stream=out)
        print(
            f"涨停买 {sk.skipped_buy_at_limit_up} · 跌停卖 {sk.skipped_sell_at_limit_down} · "
            f"状态 {sk.skipped_stock_status} · "
            f"参与率跳过买/卖 {sk.skipped_buy_participation}/{sk.skipped_sell_participation} · "
            f"砍量 {sk.clipped_buy_participation}/{sk.clipped_sell_participation}",
            file=out,
            flush=True,
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
        s = self.summary
        c = s.curves
        q = s.quality
        sk = s.skips
        wr_pct = s.win_rate * 100.0 if abs(s.win_rate) <= 1 else s.win_rate
        out: Dict[str, Any] = {
            "capitalMetrics": {
                "initialCapital": s.initial_capital,
                "finalEquity": s.final_total_equity,
                "totalReturnPct": round(s.total_return * 100.0, 2),
                "maxDrawdownPct": round(c.max_drawdown * 100.0, 2),
                "winRatePct": round(wr_pct, 2),
                "totalProfit": q.total_profit,
                "totalTrades": s.total_trades,
                "buyTrades": s.buy_trades,
                "sellTrades": s.sell_trades,
                "winTrades": q.win_trades,
                "lossTrades": q.loss_trades,
                "avgPnlPerTrade": q.avg_pnl_per_trade,
                "calmarRatio": s.calmar_ratio,
                "avgOpenPositions": c.average_open_positions,
                "peakPositions": c.peak_open_positions,
                "fullExposureDaysRatio": c.full_exposure_days_ratio_pct,
                "avgCashRatio": c.average_cash_ratio_pct,
                "capitalUtilizationRatio": c.capital_utilization_ratio_pct,
                "maxLossStreak": q.max_consecutive_losing_sells,
                "maxDrawdownDurationDays": c.max_drawdown_duration_days,
                "worstTradePnls": list(q.worst_sell_pnls),
                "stockCount": q.stock_count,
                "avgTradesPerStock": q.average_trades_per_stock,
                "top5ContributionRatio": q.top5_profit_concentration_pct,
                "stockPnlCv": q.stock_profit_coefficient_of_variation,
                "equityCurveLabels": list(c.equity_curve_labels),
                "equityCurveValues": list(c.equity_curve_values),
                "drawdownCurveValues": list(c.drawdown_curve_values),
                "skippedBuyAtLimitUp": sk.skipped_buy_at_limit_up,
                "skippedSellAtLimitDown": sk.skipped_sell_at_limit_down,
                "skippedStockStatus": sk.skipped_stock_status,
                "skippedBuyParticipation": sk.skipped_buy_participation,
                "skippedSellParticipation": sk.skipped_sell_participation,
                "clippedBuyParticipation": sk.clipped_buy_participation,
                "clippedSellParticipation": sk.clipped_sell_participation,
            },
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "version_id": self.version_id,
            "enum_version_id": self.enum_version_id,
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
    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager
        self._report: Optional[OverallReport] = None

    def build_from_sim(self, sim: Any) -> "OverallReportHandle":
        self._report = OverallReport.build_from_sim(
            sim,
            strategy_key=self._manager.strategy_key,
            strategy_path=self._manager.strategy_path,
            version_id=self._manager.version_id,
            enum_version_id=self._manager.enum_version_id,
            backtest_period=dict(self._manager._period or {}),
        )
        return self

    def save(self) -> Path:
        if self._report is None:
            raise RuntimeError("overall 未 build")
        return self._report.save(self._manager.output_dir)

    def present(self, stream: Optional[TextIO] = None) -> None:
        OverallReport.load(self._manager.output_dir).present(stream=stream)

    @property
    def report(self) -> Optional[OverallReport]:
        return self._report


if TYPE_CHECKING:
    from core.modules.strategy.core.engines.portfolio.report_manager.report_manager import (
        ReportManager,
    )


__all__ = ["OverallSummary", "OverallReport", "OverallReportHandle"]
