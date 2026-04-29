#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import json
import logging
import time

from core.modules.strategy.engines.analyzer import Analyzer
from core.modules.strategy.engines.shared.data_classes.strategy_info import StrategyInfo
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
    load_strategy_settings_view,
)
from core.modules.strategy.engines.shared.simulator_hooks_dispatcher import SimulatorHooksDispatcher
from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.account import Account, Position
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.report import CapitalReport
from core.modules.strategy.engines.simulator.capital_allocation.helpers.allocation import AllocationStrategy
from core.modules.strategy.engines.simulator.capital_allocation.helpers.core import DateTimeEncoder
from core.modules.strategy.engines.simulator.capital_allocation.helpers.fees import FeeCalculator
from core.modules.strategy.engines.simulator.helpers.enumerator_bootstrap import (
    resolve_or_build_enumerator_version,
)
from core.modules.strategy.services.artifacts import (
    DataLoader,
    ResultPathManager,
    SimulationEvent,
    VersionManager,
)

logger = logging.getLogger(__name__)


@dataclass
class CapitalAllocationSimulatorConfig:
    base_version: str = "latest"
    use_sampling: bool = True
    initial_capital: float = 1_000_000.0
    allocation_mode: str = "equal_capital"
    max_portfolio_size: int = 10
    max_weight_per_stock: float = 0.3
    lot_size: int = 100
    lots_per_trade: int = 1
    kelly_fraction: float = 0.5
    start_date: str = ""
    end_date: str = ""
    commission_rate: float = 0.00025
    min_commission: float = 5.0
    stamp_duty_rate: float = 0.001
    transfer_fee_rate: float = 0.0
    save_trades: bool = True
    save_equity_curve: bool = True

    @classmethod
    def from_settings(cls, settings: StrategySettingsView) -> "CapitalAllocationSimulatorConfig":
        cfg = settings.to_dict()
        capital_sim_cfg = cfg.get("capital_simulator", {}) or {}
        simulator_cfg = cfg.get("price_simulator", {}) or {}
        top_level_fees = cfg.get("fees", {}) or {}
        allocation_cfg = capital_sim_cfg.get("allocation", {}) or {}
        fees_cfg = capital_sim_cfg.get("fees") or simulator_cfg.get("fees") or top_level_fees or {}
        output_cfg = capital_sim_cfg.get("output", {}) or {}
        return cls(
            base_version=capital_sim_cfg.get("base_version", "latest") or "latest",
            use_sampling=bool(capital_sim_cfg.get("use_sampling", True)),
            initial_capital=float(capital_sim_cfg.get("initial_capital", 1_000_000) or 1_000_000),
            allocation_mode=allocation_cfg.get("mode", "equal_capital"),
            max_portfolio_size=int(allocation_cfg.get("max_portfolio_size", 10) or 10),
            max_weight_per_stock=float(allocation_cfg.get("max_weight_per_stock", 0.3) or 0.3),
            lot_size=int(allocation_cfg.get("lot_size", 100) or 100),
            lots_per_trade=int(allocation_cfg.get("lots_per_trade", 1) or 1),
            kelly_fraction=float(allocation_cfg.get("kelly_fraction", 0.5) or 0.5),
            commission_rate=float(fees_cfg.get("commission_rate", 0.00025) or 0.00025),
            min_commission=float(fees_cfg.get("min_commission", 5.0) or 5.0),
            stamp_duty_rate=float(fees_cfg.get("stamp_duty_rate", 0.001) or 0.001),
            transfer_fee_rate=float(fees_cfg.get("transfer_fee_rate", 0.0) or 0.0),
            save_trades=bool(output_cfg.get("save_trades", True)),
            save_equity_curve=bool(output_cfg.get("save_equity_curve", True)),
            start_date=capital_sim_cfg.get("start_date") or simulator_cfg.get("start_date") or "",
            end_date=capital_sim_cfg.get("end_date") or simulator_cfg.get("end_date") or "",
        )


class CapitalAllocationSimulator:
    def __init__(self, is_verbose: bool = False) -> None:
        self.is_verbose = is_verbose
        self.hooks_dispatcher: Optional[SimulatorHooksDispatcher] = None

    def run(
        self, strategy_name: str, strategy_info: Optional[StrategyInfo] = None
    ) -> Dict[str, Any]:
        base_settings = load_strategy_settings_view(
            strategy_name, strategy_info=strategy_info
        )
        config = CapitalAllocationSimulatorConfig.from_settings(base_settings)
        profiler = PerformanceProfiler(stock_id="capital_allocation")
        profiler.start_timer("total")

        output_version_dir, output_root = resolve_or_build_enumerator_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            use_sampling=config.use_sampling,
            base_version=config.base_version,
            strategy_info=strategy_info,
        )
        sim_version_dir, sim_version_id = VersionManager.create_capital_allocation_version(strategy_name)
        self.hooks_dispatcher = SimulatorHooksDispatcher(strategy_name)

        profiler.start_timer("load_data")
        data_loader = DataLoader(strategy_name=strategy_name, cache_enabled=True)
        events = data_loader.build_event_stream(
            output_version_dir,
            start_date=config.start_date or "",
            end_date=config.end_date or "",
        )
        profiler.metrics.time_load_data = profiler.end_timer("load_data")
        profiler.metrics.opportunity_count = len(events)
        if not events:
            return {}

        account = Account(initial_cash=config.initial_capital, cash=config.initial_capital)
        fee_calculator = FeeCalculator(
            commission_rate=config.commission_rate,
            min_commission=config.min_commission,
            stamp_duty_rate=config.stamp_duty_rate,
            transfer_fee_rate=config.transfer_fee_rate,
        )
        allocation_strategy = AllocationStrategy(
            mode=config.allocation_mode,
            initial_capital=config.initial_capital,
            max_portfolio_size=config.max_portfolio_size,
            lot_size=config.lot_size,
            lots_per_trade=config.lots_per_trade,
            kelly_fraction=config.kelly_fraction,
            fee_calculator=fee_calculator,
        )

        trades: List[Dict[str, Any]] = []
        equity_curve: List[Dict[str, Any]] = []
        current_date: Optional[str] = None
        completed_opportunities_map: Dict[str, Dict[str, Any]] = {}

        profiler.start_timer("enumerate")
        for event in events:
            if event.date != current_date:
                if current_date is not None and config.save_equity_curve:
                    equity_curve.append(
                        {
                            "date": current_date,
                            "cash_balance": account.cash,
                            "total_equity": account.get_equity({}),
                            "open_positions": account.get_portfolio_size(),
                        }
                    )
                current_date = event.date
            if event.is_trigger():
                trade = self._handle_trigger_event(event, account, allocation_strategy, completed_opportunities_map)
                if trade:
                    trades.append(trade)
            elif event.is_target():
                trade = self._handle_target_event(event, account, fee_calculator)
                if trade:
                    trades.append(trade)
                    self._update_completed_opportunities(event, completed_opportunities_map, account)
        profiler.metrics.time_enumerate = profiler.end_timer("enumerate")

        if current_date is not None and config.save_equity_curve:
            equity_curve.append(
                {
                    "date": current_date,
                    "cash_balance": account.cash,
                    "total_equity": account.get_equity({}),
                    "open_positions": account.get_portfolio_size(),
                }
            )

        summary = self._calculate_summary(
            account, trades, equity_curve, config.initial_capital, events, completed_opportunities_map
        )
        profiler.start_timer("save_csv")
        self._save_results(
            sim_version_dir,
            sim_version_id,
            output_version_dir.name,
            trades,
            equity_curve,
            summary,
            config,
            base_settings.to_dict(),
        )
        profiler.metrics.time_save_csv = profiler.end_timer("save_csv")
        profiler.metrics.time_total = profiler.end_timer("total")
        try:
            perf_path = ResultPathManager(sim_version_dir=sim_version_dir).ensure_root() / "0_performance_report.json"
            with perf_path.open("w", encoding="utf-8") as f:
                json.dump(profiler.finalize().to_dict(), f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        except Exception:
            pass
        try:
            Analyzer.run_for_simulator(
                strategy_name=strategy_name,
                sim_type="capital_allocation",
                sim_version_dir=sim_version_dir,
                raw_settings=base_settings.to_dict(),
            )
        except Exception:
            pass
        return summary

    def _handle_trigger_event(
        self, event: SimulationEvent, account: Account, allocation_strategy: AllocationStrategy, completed_opportunities_map: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        stock_id = event.stock_id
        opportunity = event.opportunity or {}
        opp_id = str(opportunity.get("opportunity_id", "")).strip()
        trigger_price = float(opportunity.get("trigger_price", 0.0) or 0.0)
        if not stock_id or not opp_id or trigger_price <= 0:
            return None
        if account.has_position(stock_id) or account.get_portfolio_size() >= allocation_strategy.max_portfolio_size:
            return None
        win_rate = self._calculate_win_rate(completed_opportunities_map) if allocation_strategy.mode == "kelly" else None
        buy_shares = allocation_strategy.calculate_shares_to_buy(account, trigger_price, win_rate)
        if buy_shares == 0:
            return None
        gross_amount = buy_shares * trigger_price
        fees = allocation_strategy.fee_calculator.calculate_fees(gross_amount, "buy")
        total_cost = gross_amount + fees
        if account.cash < total_cost:
            return None
        account.cash -= total_cost
        position = account.positions.get(stock_id) or Position(stock_id=stock_id)
        account.positions[stock_id] = position
        position.shares = buy_shares
        position.avg_cost = total_cost / buy_shares
        position.current_opportunity_id = opp_id
        return {
            "date": event.date,
            "stock_id": stock_id,
            "opportunity_id": opp_id,
            "side": "buy",
            "shares": buy_shares,
            "price": trigger_price,
            "amount": gross_amount,
            "fees": fees,
            "total_cost": total_cost,
            "cash_after": account.cash,
            "equity_after": account.get_equity({stock_id: trigger_price}),
        }

    def _handle_target_event(self, event: SimulationEvent, account: Account, fee_calculator: FeeCalculator) -> Optional[Dict[str, Any]]:
        stock_id = event.stock_id
        target = event.target or {}
        opp_id = str(target.get("opportunity_id", "")).strip()
        raw_sell_price = target.get("sell_price", 0.0) or target.get("price", 0.0) or target.get("target_price", 0.0)
        sell_price = float(raw_sell_price or 0.0)
        if not stock_id or not opp_id or sell_price <= 0:
            return None
        position = account.get_position(stock_id)
        if not position or position.shares == 0 or position.current_opportunity_id != opp_id:
            return None
        raw_sell_ratio = target.get("sell_ratio", 0.0)
        try:
            sell_ratio = float(raw_sell_ratio if raw_sell_ratio not in (None, "", 0) else 1.0)
        except (TypeError, ValueError):
            sell_ratio = 1.0
        sell_shares = int(position.shares * sell_ratio)
        if sell_shares == 0:
            return None
        gross_amount = sell_shares * sell_price
        fees = fee_calculator.calculate_fees(gross_amount, "sell")
        net_proceeds = gross_amount - fees
        cost = sell_shares * position.avg_cost
        pnl = net_proceeds - cost
        account.cash += net_proceeds
        position.shares -= sell_shares
        position.realized_pnl += pnl
        if position.shares == 0:
            position.current_opportunity_id = None
        return {
            "date": event.date,
            "stock_id": stock_id,
            "opportunity_id": opp_id,
            "side": "sell",
            "shares": sell_shares,
            "price": sell_price,
            "amount": gross_amount,
            "fees": fees,
            "net_proceeds": net_proceeds,
            "pnl": pnl,
            "cash_after": account.cash,
            "equity_after": account.get_equity({stock_id: sell_price}),
        }

    def _calculate_win_rate(self, completed_opportunities_map: Dict[str, Dict[str, Any]]) -> float:
        if not completed_opportunities_map:
            return 0.5
        opportunities = list(completed_opportunities_map.values())
        win_count = sum(1 for opp in opportunities if float(opp.get("roi", 0) or 0) > 0)
        return win_count / len(opportunities) if opportunities else 0.5

    def _update_completed_opportunities(self, event: SimulationEvent, completed_opportunities_map: Dict[str, Dict[str, Any]], account: Account) -> None:
        target = event.target or {}
        opp_id = str(target.get("opportunity_id", "")).strip()
        if not opp_id:
            return
        position = account.get_position(event.stock_id)
        if position and position.current_opportunity_id == opp_id and position.shares == 0:
            opportunity = event.opportunity or {}
            if opportunity and opp_id not in completed_opportunities_map:
                completed_opportunities_map[opp_id] = opportunity

    def _calculate_summary(
        self,
        account: Account,
        trades: List[Dict[str, Any]],
        equity_curve: List[Dict[str, Any]],
        initial_capital: float,
        events: List[SimulationEvent],
        completed_opportunities_map: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        final_equity = equity_curve[-1].get("total_equity", account.cash) if equity_curve else account.cash
        total_return = (final_equity - initial_capital) / initial_capital if initial_capital > 0 else 0.0
        max_drawdown = 0.0
        if equity_curve:
            peak = initial_capital
            for point in equity_curve:
                equity = point.get("total_equity", initial_capital)
                if equity > peak:
                    peak = equity
                max_drawdown = max(max_drawdown, (peak - equity) / peak if peak > 0 else 0.0)
        buy_trades = [t for t in trades if t.get("side") == "buy"]
        sell_trades = [t for t in trades if t.get("side") == "sell"]
        win_trades = [t for t in sell_trades if t.get("pnl", 0) > 0]
        loss_trades = [t for t in sell_trades if t.get("pnl", 0) < 0]
        stock_summary = defaultdict(lambda: {"trade_count": 0, "total_profit": 0.0, "win_trades": 0, "loss_trades": 0})
        for trade in sell_trades:
            stock_id = trade.get("stock_id", "")
            stock_summary[stock_id]["trade_count"] += 1
            stock_summary[stock_id]["total_profit"] += trade.get("pnl", 0.0)
            if trade.get("pnl", 0) > 0:
                stock_summary[stock_id]["win_trades"] += 1
            else:
                stock_summary[stock_id]["loss_trades"] += 1
        trigger_ids = {str(e.opportunity_id or "").strip() for e in events if e.is_trigger() and str(e.opportunity_id or "").strip()}
        completed_ids = {str(opp_id).strip() for opp_id in completed_opportunities_map.keys() if str(opp_id).strip()}
        total_opportunities = len(trigger_ids)
        completed_opportunities = len(trigger_ids & completed_ids)
        unfinished_opportunities = max(total_opportunities - completed_opportunities, 0)
        raw_summary = {
            "initial_capital": initial_capital,
            "final_cash_balance": account.cash,
            "final_total_equity": final_equity,
            "final_equity": final_equity,
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "total_trades": len(trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "win_trades": len(win_trades),
            "loss_trades": len(loss_trades),
            "win_rate": len(win_trades) / len(sell_trades) if sell_trades else 0.0,
            "total_profit": sum(t.get("pnl", 0.0) for t in sell_trades),
            "total_opportunities": total_opportunities,
            "completed_opportunities": completed_opportunities,
            "unfinished_opportunities": unfinished_opportunities,
            "completion_rate": (completed_opportunities / total_opportunities) if total_opportunities > 0 else 0.0,
            "stock_summary": dict(stock_summary),
        }
        return CapitalReport.from_dict(raw_summary).to_dict()

    def _save_results(
        self,
        sim_version_dir: Path,
        sim_version_id: int,
        output_version: str,
        trades: List[Dict[str, Any]],
        equity_curve: List[Dict[str, Any]],
        summary: Dict[str, Any],
        config: CapitalAllocationSimulatorConfig,
        settings_snapshot: Dict[str, Any],
    ) -> None:
        from core.utils.io.csv_io import write_dicts_to_csv

        path_mgr = ResultPathManager(sim_version_dir=sim_version_dir)
        if config.save_trades and trades:
            trades_path = path_mgr.trades_path()
            with trades_path.open("w", encoding="utf-8") as f:
                json.dump(trades, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
            write_dicts_to_csv(trades_path.with_suffix(".csv"), trades)
        if config.save_equity_curve and equity_curve:
            equity_path = path_mgr.equity_timeseries_path()
            with equity_path.open("w", encoding="utf-8") as f:
                json.dump(equity_curve, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
            write_dicts_to_csv(equity_path.with_suffix(".csv"), equity_curve)
        with path_mgr.strategy_summary_path().open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        metadata = {
            "sim_version": f"{sim_version_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "output_version": output_version,
            "config": config.__dict__,
            "settings_snapshot": settings_snapshot,
            "created_at": datetime.now().isoformat(),
        }
        with path_mgr.metadata_path().open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)


__all__ = ["CapitalAllocationSimulatorConfig", "CapitalAllocationSimulator"]
