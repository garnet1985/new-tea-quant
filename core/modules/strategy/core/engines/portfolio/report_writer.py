"""Portfolio 回放产物落盘（类导出）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimResult

_OVERALL_REPORT = "0_overall_report.json"
_TRADES_FILE = "trades.json"
_EQUITY_FILE = "equity_curve.json"


@dataclass
class PortfolioReportWriter:
    """写 trades / equity / overall，并组装可缓存 report dict。"""

    output_dir: Path
    strategy_key: str
    strategy_path: str
    version_id: int
    enum_version_id: str

    def finalize(
        self,
        sim: PortfolioSimResult,
        *,
        period: Dict[str, str],
        save_trades: bool = True,
        save_equity_curve: bool = True,
    ) -> Dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if save_trades:
            self._write_json(
                self.output_dir / _TRADES_FILE,
                [t.to_dict() for t in sim.trades],
            )
        if save_equity_curve:
            self._write_json(self.output_dir / _EQUITY_FILE, list(sim.equity_curve))

        summary = self._build_summary(sim, period=period)
        overall = {
            "summary": summary,
            "period": dict(period or {}),
            "enum_version_id": self.enum_version_id,
            "version_id": int(self.version_id),
        }
        self._write_json(self.output_dir / _OVERALL_REPORT, overall)

        return {
            "success": bool(sim.success),
            "output_dir": str(self.output_dir),
            "version_id": int(self.version_id),
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "enum_version_id": self.enum_version_id,
            "period": dict(period or {}),
            "summary": summary,
            "trade_count": len(sim.trades),
            "skipped_buys": int(sim.skipped_buys),
            "skipped_sells": int(sim.skipped_sells),
            "buy_participation_skip": int(sim.buy_participation_skip),
            "buy_participation_clipped": int(sim.buy_participation_clipped),
            "sell_participation_skip": int(sim.sell_participation_skip),
            "sell_participation_clipped": int(sim.sell_participation_clipped),
        }

    def _build_summary(
        self,
        sim: PortfolioSimResult,
        *,
        period: Dict[str, str],
    ) -> Dict[str, Any]:
        account = sim.account
        initial = float(account.initial_cash)
        final_equity = float(account.equity({}))
        total_return = (final_equity / initial - 1.0) if initial > 0 else 0.0
        sell_profits = [
            float(t.profit or 0.0) for t in sim.trades if t.is_sell() and t.profit is not None
        ]
        win_rate = (
            (float(sim.win_count) / float(sim.completed_count))
            if sim.completed_count > 0
            else 0.0
        )
        return {
            "initial_capital": initial,
            "final_cash": float(account.cash),
            "final_equity": final_equity,
            "total_return": total_return,
            "total_trades": len(sim.trades),
            "buy_trades": sum(1 for t in sim.trades if t.is_buy()),
            "sell_trades": sum(1 for t in sim.trades if t.is_sell()),
            "completed_investments": int(sim.completed_count),
            "open_positions": int(account.open_position_count()),
            "win_count": int(sim.win_count),
            "win_rate": win_rate,
            "realized_profit": float(sum(sell_profits)),
            "skipped_buys": int(sim.skipped_buys),
            "skipped_sells": int(sim.skipped_sells),
            "buy_participation_skip": int(sim.buy_participation_skip),
            "buy_participation_clipped": int(sim.buy_participation_clipped),
            "sell_participation_skip": int(sim.sell_participation_skip),
            "sell_participation_clipped": int(sim.sell_participation_clipped),
            "period": dict(period or {}),
        }

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


__all__ = ["PortfolioReportWriter"]
