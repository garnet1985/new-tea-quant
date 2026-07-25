"""Portfolio 回放产物编排（version 目录 + trades / equity / overall）。

本文件:
- ReportManager: begin / summarize / save / finalize / present
  边界: 负责 portfolio 落盘与展示；不负责 simulate 逻辑
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TextIO, TYPE_CHECKING

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    OVERALL_REPORT_FILE,
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)
from core.system import get_version

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimResult
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import (
        SimulateSession,
    )
    from core.modules.strategy.core.engines.shared.services.simulation_output.enum_source import (
        EnumSource,
    )

_TRADES_FILE = "trades.json"
_EQUITY_FILE = "equity_curve.json"
_DEFAULT_MARKET_PROFILE = "china_a_stock"


@dataclass
class ReportManager(BaseReportManager):
    """Portfolio 产物编排（合并原 Handle + Writer）。

    边界:
    - 负责: version 目录、runtime/overall/trades/equity 落盘、present
    - 不负责: 事件构建 / 账户回放
    - 调用方: PortfolioPipeline
    """

    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    enum_version_id: str = ""
    market_profile: str = _DEFAULT_MARKET_PROFILE
    _sim: Any = field(default=None, init=False, repr=False)
    _period: Dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _save_trades: bool = field(default=True, init=False, repr=False)
    _save_equity_curve: bool = field(default=True, init=False, repr=False)
    _summary: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _report_dict: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def begin(
        cls,
        ctx: "SimulateSession",
        data: "EnumSource",
    ) -> "ReportManager":
        """分配 ``simulations/portfolio/{strategy}/{version}``，写 runtime。"""
        info = ctx.strategy_info
        strategy_key = str(getattr(info, "key", "") or "").strip()
        strategy_path = str(
            getattr(info, "unique_relative_path", "") or ctx.strategy_key or ""
        ).strip()
        if not strategy_path:
            raise ValueError("strategy_path 不能为空")

        root = ProjectContext.path.get_strategy_directory_simulation_portfolio(
            strategy_path
        )
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            strategy_path,
            root,
        )
        market_profile = (
            str(data.runtime.market_profile or "").strip() or _DEFAULT_MARKET_PROFILE
        )
        runtime = {
            "strategy_key": strategy_key or strategy_path,
            "strategy_path": strategy_path,
            "version_id": int(version_id),
            "enum_version_id": str(data.version_id),
            "enum_output_dir": str(data.output_dir),
            "settings_fp": str(ctx.settings_fp or ""),
            "env_fp": str(ctx.env_fp or ""),
            "period": {
                "start_date": data.start_date,
                "end_date": data.end_date,
            },
            "entity_ids": list(data.entity_ids),
            "entity_count": len(data.entity_ids),
            "market_profile": market_profile,
            "engine_version": get_version(),
            "created_at": datetime.now().isoformat(),
            "kind": "portfolio",
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / RUNTIME_ENV_FILE).write_text(
            json.dumps(runtime, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return cls(
            output_dir=output_dir,
            strategy_key=strategy_key or strategy_path,
            strategy_path=strategy_path,
            version_id=int(version_id),
            enum_version_id=str(data.version_id),
            market_profile=market_profile,
        )

    def summarize(self) -> Dict[str, Any]:
        sim = self._sim
        if sim is None:
            self._summary = {}
            return self._summary
        account = sim.account
        initial = float(account.initial_cash)
        final_equity = float(account.equity({}))
        total_return = (final_equity / initial - 1.0) if initial > 0 else 0.0
        sell_profits = [
            float(t.profit or 0.0)
            for t in sim.trades
            if t.is_sell() and t.profit is not None
        ]
        win_rate = (
            (float(sim.win_count) / float(sim.completed_count))
            if sim.completed_count > 0
            else 0.0
        )
        self._summary = {
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
            "period": dict(self._period or {}),
        }
        return self._summary

    def save(self) -> Dict[str, Any]:
        sim = self._sim
        if sim is None:
            return {}
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self._save_trades:
            self._write_json(
                self.output_dir / _TRADES_FILE,
                [t.to_dict() for t in sim.trades],
            )
        if self._save_equity_curve:
            self._write_json(
                self.output_dir / _EQUITY_FILE,
                list(sim.equity_curve),
            )
        if not self._summary:
            self.summarize()
        overall = {
            "summary": self._summary,
            "period": dict(self._period or {}),
            "enum_version_id": self.enum_version_id,
            "version_id": int(self.version_id),
        }
        self._write_json(self.output_dir / OVERALL_REPORT_FILE, overall)
        self._report_dict = {
            "success": bool(sim.success),
            "output_dir": str(self.output_dir),
            "version_id": int(self.version_id),
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "enum_version_id": self.enum_version_id,
            "period": dict(self._period or {}),
            "summary": self._summary,
            "trade_count": len(sim.trades),
            "skipped_buys": int(sim.skipped_buys),
            "skipped_sells": int(sim.skipped_sells),
            "buy_participation_skip": int(sim.buy_participation_skip),
            "buy_participation_clipped": int(sim.buy_participation_clipped),
            "sell_participation_skip": int(sim.sell_participation_skip),
            "sell_participation_clipped": int(sim.sell_participation_clipped),
        }
        return self._report_dict

    def finalize(
        self,
        sim: "PortfolioSimResult" = None,  # type: ignore[assignment]
        *,
        period: Optional[Dict[str, str]] = None,
        save_trades: bool = True,
        save_equity_curve: bool = True,
        present: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        _ = kwargs
        self._sim = sim
        self._period = dict(period or {})
        self._save_trades = bool(save_trades)
        self._save_equity_curve = bool(save_equity_curve)
        self.summarize()
        result = self.save()
        if present:
            self.present()
        return result

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        summary = dict(self._summary or (self._report_dict or {}).get("summary") or {})
        period = dict(self._period or summary.get("period") or {})
        print(
            f"portfolio: {self.strategy_key} v{self.version_id}  "
            f"path={self.strategy_path or '-'}  "
            f"period={period.get('start_date', '')}~{period.get('end_date', '')}",
            file=out,
            flush=True,
        )
        print(
            f"capital: {summary.get('initial_capital', '?')} → "
            f"{summary.get('final_equity', '?')}  "
            f"return={summary.get('total_return', '?')}  "
            f"trades={summary.get('total_trades', 0)}  "
            f"win_rate={summary.get('win_rate', '?')}",
            file=out,
            flush=True,
        )
        print(f"产物目录: {self.output_dir}", file=out, flush=True)

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# 兼容旧名
PortfolioReportWriter = ReportManager
PortfolioReportHandle = ReportManager

__all__ = ["ReportManager", "PortfolioReportWriter", "PortfolioReportHandle"]
