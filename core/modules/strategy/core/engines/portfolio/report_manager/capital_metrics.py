"""Portfolio 衍生指标（曲线 / 回撤 / 利用率 / 集中度）。

边界: 纯计算；无 IO。调用方: OverallReport / EntityListReport build。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple


@dataclass
class EquityCurves:
    """权益 / 回撤曲线（可降采样）。"""

    equity_curve_labels: List[str] = field(default_factory=list)
    equity_curve_values: List[float] = field(default_factory=list)
    drawdown_curve_values: List[float] = field(default_factory=list)
    max_drawdown: float = 0.0
    max_drawdown_duration_days: int = 0
    average_open_positions: float = 0.0
    peak_open_positions: int = 0
    full_exposure_days_ratio_pct: float = 0.0
    average_cash_ratio_pct: float = 0.0
    capital_utilization_ratio_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "equity_curve_labels": list(self.equity_curve_labels),
            "equity_curve_values": list(self.equity_curve_values),
            "drawdown_curve_values": list(self.drawdown_curve_values),
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration_days": self.max_drawdown_duration_days,
            "average_open_positions": self.average_open_positions,
            "peak_open_positions": self.peak_open_positions,
            "full_exposure_days_ratio_pct": self.full_exposure_days_ratio_pct,
            "average_cash_ratio_pct": self.average_cash_ratio_pct,
            "capital_utilization_ratio_pct": self.capital_utilization_ratio_pct,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "EquityCurves":
        data = raw or {}
        return cls(
            equity_curve_labels=[str(x) for x in (data.get("equity_curve_labels") or [])],
            equity_curve_values=[
                float(v or 0.0) for v in (data.get("equity_curve_values") or [])
            ],
            drawdown_curve_values=[
                float(v or 0.0) for v in (data.get("drawdown_curve_values") or [])
            ],
            max_drawdown=float(data.get("max_drawdown") or 0.0),
            max_drawdown_duration_days=int(data.get("max_drawdown_duration_days") or 0),
            average_open_positions=float(data.get("average_open_positions") or 0.0),
            peak_open_positions=int(data.get("peak_open_positions") or 0),
            full_exposure_days_ratio_pct=float(
                data.get("full_exposure_days_ratio_pct") or 0.0
            ),
            average_cash_ratio_pct=float(data.get("average_cash_ratio_pct") or 0.0),
            capital_utilization_ratio_pct=float(
                data.get("capital_utilization_ratio_pct") or 0.0
            ),
        )

    @classmethod
    def downsample_indices(cls, n: int, max_points: int = 80) -> List[int]:
        if n <= 0:
            return []
        if n <= max_points:
            return list(range(n))
        out: List[int] = []
        for k in range(max_points):
            idx = int(round(k * (n - 1) / max(1, max_points - 1)))
            out.append(min(idx, n - 1))
        return sorted(set(out))

    @classmethod
    def point_equity(cls, point: Dict[str, Any]) -> float:
        return float(
            point.get("equity")
            if point.get("equity") is not None
            else point.get("total_equity")
            or 0.0
        )

    @classmethod
    def point_cash(cls, point: Dict[str, Any]) -> float:
        return float(
            point.get("cash")
            if point.get("cash") is not None
            else point.get("cash_balance")
            or 0.0
        )

    @classmethod
    def compute(
        cls,
        equity_curve: Sequence[Dict[str, Any]],
        *,
        initial_capital: float,
    ) -> "EquityCurves":
        points = list(equity_curve or [])
        ic = float(initial_capital or 0.0)
        if not points and ic >= 0:
            points = [
                {"date": "期初", "cash": ic, "equity": ic, "open_positions": 0},
                {"date": "期末", "cash": ic, "equity": ic, "open_positions": 0},
            ]

        labels_full: List[str] = []
        vals_full: List[float] = []
        opens_full: List[float] = []
        cash_ratio_full: List[float] = []
        peak = ic
        max_dd = 0.0
        for p in points:
            labels_full.append(str(p.get("date") or "")[:16])
            eq = cls.point_equity(p)
            vals_full.append(eq)
            opens_full.append(float(p.get("open_positions") or 0))
            te = eq if eq > 1e-9 else 1.0
            cash_ratio_full.append(cls.point_cash(p) / te * 100.0)
            peak = max(peak, eq)
            dd = ((peak - eq) / peak) if peak > 1e-9 else 0.0
            max_dd = max(max_dd, dd)

        peak_run = ic
        drawdown_full: List[float] = []
        for v in vals_full:
            peak_run = max(peak_run, v)
            dd_pct = ((peak_run - v) / peak_run * 100.0) if peak_run > 1e-9 else 0.0
            drawdown_full.append(round(dd_pct, 4))

        idxs = cls.downsample_indices(len(vals_full), 80)
        peak_open = max(opens_full) if opens_full else 0.0
        avg_open = sum(opens_full) / len(opens_full) if opens_full else 0.0
        n_days = len(opens_full)
        full_exp_days = (
            sum(1 for o in opens_full if peak_open > 0 and o >= peak_open - 0.5)
            if peak_open > 0
            else 0
        )
        avg_cash = sum(cash_ratio_full) / len(cash_ratio_full) if cash_ratio_full else 0.0
        cap_util = max(0.0, min(100.0, 100.0 - avg_cash))

        max_dd_duration = 0
        run_len = 0
        for dd in drawdown_full:
            if dd > 0.5:
                run_len += 1
                max_dd_duration = max(max_dd_duration, run_len)
            else:
                run_len = 0

        return cls(
            equity_curve_labels=[labels_full[i] for i in idxs],
            equity_curve_values=[vals_full[i] for i in idxs],
            drawdown_curve_values=[drawdown_full[i] for i in idxs],
            max_drawdown=round(max_dd, 6),
            max_drawdown_duration_days=int(max_dd_duration),
            average_open_positions=round(avg_open, 3),
            peak_open_positions=int(round(peak_open)),
            full_exposure_days_ratio_pct=round(
                (full_exp_days / n_days * 100.0) if n_days else 0.0, 2
            ),
            average_cash_ratio_pct=round(avg_cash, 2),
            capital_utilization_ratio_pct=round(cap_util, 2),
        )


@dataclass
class TradeQualityMetrics:
    """成交质量 / 风险尾部。"""

    win_trades: int = 0
    loss_trades: int = 0
    total_profit: float = 0.0
    avg_pnl_per_trade: float = 0.0
    max_consecutive_losing_sells: int = 0
    worst_sell_pnls: List[float] = field(default_factory=list)
    stock_count: int = 0
    average_trades_per_stock: float = 0.0
    top5_profit_concentration_pct: float = 0.0
    stock_profit_coefficient_of_variation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "win_trades": self.win_trades,
            "loss_trades": self.loss_trades,
            "total_profit": self.total_profit,
            "avg_pnl_per_trade": self.avg_pnl_per_trade,
            "max_consecutive_losing_sells": self.max_consecutive_losing_sells,
            "worst_sell_pnls": list(self.worst_sell_pnls),
            "stock_count": self.stock_count,
            "average_trades_per_stock": self.average_trades_per_stock,
            "top5_profit_concentration_pct": self.top5_profit_concentration_pct,
            "stock_profit_coefficient_of_variation": (
                self.stock_profit_coefficient_of_variation
            ),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TradeQualityMetrics":
        data = raw or {}
        return cls(
            win_trades=int(data.get("win_trades") or 0),
            loss_trades=int(data.get("loss_trades") or 0),
            total_profit=float(data.get("total_profit") or 0.0),
            avg_pnl_per_trade=float(data.get("avg_pnl_per_trade") or 0.0),
            max_consecutive_losing_sells=int(
                data.get("max_consecutive_losing_sells") or 0
            ),
            worst_sell_pnls=[
                float(v or 0.0) for v in (data.get("worst_sell_pnls") or [])
            ],
            stock_count=int(data.get("stock_count") or 0),
            average_trades_per_stock=float(data.get("average_trades_per_stock") or 0.0),
            top5_profit_concentration_pct=float(
                data.get("top5_profit_concentration_pct") or 0.0
            ),
            stock_profit_coefficient_of_variation=float(
                data.get("stock_profit_coefficient_of_variation") or 0.0
            ),
        )

    @classmethod
    def _profit_cv(cls, values: Sequence[float]) -> float:
        vals = [float(v) for v in values]
        if len(vals) < 2:
            return 0.0
        mean = sum(vals) / len(vals)
        if abs(mean) < 1e-12:
            return 0.0
        var = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
        return (var**0.5) / abs(mean)

    @classmethod
    def compute(
        cls,
        trades: Sequence[Any],
        *,
        per_entity_profit: Dict[str, float],
        per_entity_sells: Dict[str, int],
    ) -> "TradeQualityMetrics":
        sells = [t for t in trades if getattr(t, "is_sell", lambda: False)()]
        pnls = [float(getattr(t, "profit", 0.0) or 0.0) for t in sells]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        total_profit = sum(pnls)
        avg = (total_profit / float(len(pnls))) if pnls else 0.0

        worst = sorted(pnls)[:3]
        while len(worst) < 3:
            worst.append(0.0)

        streak = 0
        max_streak = 0
        for t in sorted(sells, key=lambda x: str(getattr(x, "date", "") or "")):
            pnl = float(getattr(t, "profit", 0.0) or 0.0)
            if pnl < 0:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

        profits = list(per_entity_profit.values())
        positive = [x for x in profits if x > 0]
        positive_sum = sum(positive)
        top5 = sum(sorted(positive, reverse=True)[:5])
        stock_cnt = len(per_entity_profit)
        sell_n = sum(per_entity_sells.values())
        return cls(
            win_trades=wins,
            loss_trades=losses,
            total_profit=round(total_profit, 2),
            avg_pnl_per_trade=round(avg, 2),
            max_consecutive_losing_sells=int(max_streak),
            worst_sell_pnls=[round(x, 2) for x in worst[:3]],
            stock_count=stock_cnt,
            average_trades_per_stock=round(
                (float(sell_n) / float(stock_cnt)) if stock_cnt else 0.0, 4
            ),
            top5_profit_concentration_pct=round(
                (top5 / positive_sum * 100.0) if positive_sum > 1e-9 else 0.0, 2
            ),
            stock_profit_coefficient_of_variation=round(cls._profit_cv(profits), 4),
        )


@dataclass
class SkipMetrics:
    """执行跳过（对齐 UI executionSkips）。"""

    skipped_buy_at_limit_up: int = 0
    skipped_sell_at_limit_down: int = 0
    skipped_stock_status: int = 0
    skipped_buy_participation: int = 0
    skipped_sell_participation: int = 0
    clipped_buy_participation: int = 0
    clipped_sell_participation: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skipped_buy_at_limit_up": self.skipped_buy_at_limit_up,
            "skipped_sell_at_limit_down": self.skipped_sell_at_limit_down,
            "skipped_stock_status": self.skipped_stock_status,
            "skipped_buy_participation": self.skipped_buy_participation,
            "skipped_sell_participation": self.skipped_sell_participation,
            "clipped_buy_participation": self.clipped_buy_participation,
            "clipped_sell_participation": self.clipped_sell_participation,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "SkipMetrics":
        data = raw or {}
        return cls(
            skipped_buy_at_limit_up=int(data.get("skipped_buy_at_limit_up") or 0),
            skipped_sell_at_limit_down=int(data.get("skipped_sell_at_limit_down") or 0),
            skipped_stock_status=int(data.get("skipped_stock_status") or 0),
            skipped_buy_participation=int(data.get("skipped_buy_participation") or 0),
            skipped_sell_participation=int(data.get("skipped_sell_participation") or 0),
            clipped_buy_participation=int(data.get("clipped_buy_participation") or 0),
            clipped_sell_participation=int(data.get("clipped_sell_participation") or 0),
        )

    @classmethod
    def from_sim(cls, sim: Any) -> "SkipMetrics":
        # 当前 simulator 未拆涨跌停/状态；参与率跳过单独计数
        return cls(
            skipped_buy_at_limit_up=0,
            skipped_sell_at_limit_down=0,
            skipped_stock_status=0,
            skipped_buy_participation=int(getattr(sim, "buy_participation_skip", 0) or 0),
            skipped_sell_participation=int(
                getattr(sim, "sell_participation_skip", 0) or 0
            ),
            clipped_buy_participation=int(
                getattr(sim, "buy_participation_clipped", 0) or 0
            ),
            clipped_sell_participation=int(
                getattr(sim, "sell_participation_clipped", 0) or 0
            ),
        )


__all__ = [
    "EquityCurves",
    "TradeQualityMetrics",
    "SkipMetrics",
]
