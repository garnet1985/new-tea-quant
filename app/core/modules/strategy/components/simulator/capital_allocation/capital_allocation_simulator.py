#!/usr/bin/env python3
"""
Capital Allocation Simulator 主类

在真实资金约束下，对枚举器 SOT 结果进行全市场回放的资金分配型模拟器。
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict
import json
import logging
from datetime import datetime

from .capital_allocation_simulator_config import CapitalAllocationSimulatorConfig
from app.core.modules.strategy.managers.version_manager import VersionManager
from app.core.modules.strategy.managers.data_loader import DataLoader
from app.core.modules.strategy.managers.result_path_manager import ResultPathManager
from app.core.modules.strategy.components.simulator.base.simulator_hooks_dispatcher import (
    SimulatorHooksDispatcher,
)
from app.core.modules.strategy.models.account import Account, Position
from app.core.modules.strategy.models.event import Event
from .fee_calculator import FeeCalculator
from .allocation_strategy import AllocationStrategy
from .helpers import DateTimeEncoder


logger = logging.getLogger(__name__)


class CapitalAllocationSimulator:
    """
    CapitalAllocationSimulator 主入口类（单进程）

    主要职责：
    - 解析策略 settings，构建 CapitalAllocationSimulatorConfig
    - 解析并选择 SOT 版本目录
    - 构建全局事件流
    - 执行单进程主循环（处理 trigger 和 target 事件）
    - 保存交易记录、权益曲线和汇总结果
    """

    def __init__(self, is_verbose: bool = False) -> None:
        self.is_verbose = is_verbose
        self.hooks_dispatcher: Optional[SimulatorHooksDispatcher] = None

    def run(self, strategy_name: str) -> Dict[str, Any]:
        """
        运行 CapitalAllocationSimulator

        Args:
            strategy_name: 策略名称（对应 userspace/strategies/{strategy_name}）

        Returns:
            summary: 模拟结果摘要
        """
        # 1. 加载策略 settings
        import importlib

        settings_module_path = f"app.userspace.strategies.{strategy_name}.settings"
        try:
            settings_module = importlib.import_module(settings_module_path)
        except ModuleNotFoundError as e:
            raise ValueError(
                f"[CapitalAllocationSimulator] 无法加载策略 settings: {settings_module_path}"
            ) from e

        raw_settings = getattr(settings_module, "settings", None)
        if not isinstance(raw_settings, dict):
            raise ValueError(
                f"[CapitalAllocationSimulator] 策略 {strategy_name} 的 settings.py 中缺少 'settings' 字典"
            )

        from app.core.modules.strategy.models.strategy_settings import StrategySettings

        base_settings = StrategySettings.from_dict(raw_settings)
        config = CapitalAllocationSimulatorConfig.from_settings(base_settings)

        # 2. 解析 SOT 版本目录
        sot_version_dir, _ = VersionManager.resolve_sot_version(
            strategy_name, config.sot_version
        )
        logger.info(
            f"[CapitalAllocationSimulator] 使用 SOT 版本: strategy={strategy_name}, "
            f"sot_version={sot_version_dir.name}"
        )

        # 3. 创建模拟器版本目录
        sim_version_dir, sim_version_id = VersionManager.create_capital_allocation_version(
            strategy_name
        )
        logger.info(
            f"[CapitalAllocationSimulator] 模拟器版本: {sim_version_dir.name} (version_id={sim_version_id})"
        )

        # 4. 初始化钩子分发器
        self.hooks_dispatcher = SimulatorHooksDispatcher(strategy_name)

        # 5. 创建 DataLoader 并构建事件流
        data_loader = DataLoader(strategy_name=strategy_name, cache_enabled=True)
        events = data_loader.build_event_stream(
            sot_version_dir,
            start_date=config.start_date or "",
            end_date=config.end_date or "",
        )

        if not events:
            logger.warning(
                f"[CapitalAllocationSimulator] 未找到任何事件: {sot_version_dir}"
            )
            return {}

        # 6. 根据 use_sampling 配置过滤事件（只保留采样股票的事件）
        if config.use_sampling:
            from app.core.modules.data_manager import DataManager
            from app.core.modules.strategy.helper.stock_sampling_helper import (
                StockSamplingHelper,
            )

            data_mgr = DataManager(is_verbose=False)
            all_stocks_info = data_mgr.service.stock.list.load(filtered=True)

            sampling_cfg = base_settings.sampling or {}
            sampling_strategy = sampling_cfg.get("strategy", "continuous")
            sampling_amount = int(sampling_cfg.get("sampling_amount", 20))

            # 获取采样后的股票列表
            sampled_stock_ids = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks_info,
                sampling_amount=sampling_amount,
                sampling_config=sampling_cfg,
            )
            sampled_stock_set = set(sampled_stock_ids)

            # 过滤事件，只保留采样后的股票
            original_count = len(events)
            events = [
                e for e in events
                if e.get("stock_id") in sampled_stock_set
            ]

            logger.info(
                f"[CapitalAllocationSimulator] 采样模式: "
                f"strategy={sampling_strategy}, amount={sampling_amount}, "
                f"原始={original_count} 个事件, 采样后={len(events)} 个事件 "
                f"(涉及 {len(sampled_stock_set)} 只股票)"
            )
        else:
            # 统计涉及的股票数量
            stock_ids = set(e.get("stock_id") for e in events)
            logger.info(
                f"[CapitalAllocationSimulator] 全量模式: {len(events)} 个事件 "
                f"(涉及 {len(stock_ids)} 只股票)"
            )

        # 7. 初始化账户和策略
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

        # 8. 执行主循环
        trades: List[Dict[str, Any]] = []
        equity_curve: List[Dict[str, Any]] = []
        current_date: Optional[str] = None

        # 用于计算 Kelly 模式的胜率（存储已完成机会的 ROI）
        # key: opportunity_id, value: opportunity dict
        completed_opportunities_map: Dict[str, Dict[str, Any]] = {}

        for event in events:
            event_date = event.date
            event_type = event.event_type

            # 如果是新的一天，更新权益曲线
            if event_date != current_date:
                if current_date is not None and config.save_equity_curve:
                    stock_prices = self._get_stock_prices_for_date(
                        account, event.opportunity or (event.target or {})
                    )
                    equity = account.get_equity(stock_prices)
                    equity_curve.append({
                        "date": current_date,
                        "cash": account.cash,
                        "equity": equity,
                        "portfolio_size": account.get_portfolio_size(),
                    })
                current_date = event_date

            # 处理事件
            if event.is_trigger():
                trade = self._handle_trigger_event(
                    event, account, allocation_strategy, completed_opportunities_map
                )
                if trade:
                    trades.append(trade)
            elif event.is_target():
                trade = self._handle_target_event(event, account, fee_calculator)
                if trade:
                    trades.append(trade)
                    # 更新已完成机会（用于 Kelly 模式）
                    self._update_completed_opportunities(
                        event, completed_opportunities_map, account
                    )

        # 记录最后一天的权益
        if current_date is not None and config.save_equity_curve:
            stock_prices = {}
            for stock_id, position in account.positions.items():
                if position.shares > 0:
                    stock_prices[stock_id] = position.avg_cost  # 使用成本价作为最后估值
            equity = account.get_equity(stock_prices)
            equity_curve.append({
                "date": current_date,
                "cash": account.cash,
                "equity": equity,
                "portfolio_size": account.get_portfolio_size(),
            })

        # 9. 计算汇总统计
        summary = self._calculate_summary(
            account, trades, equity_curve, config.initial_capital
        )

        # 10. 保存结果
        self._save_results(
            sim_version_dir,
            sim_version_id,
            sot_version_dir.name,
            trades,
            equity_curve,
            summary,
            config,
            base_settings.to_dict(),
        )

        logger.info(
            f"[CapitalAllocationSimulator] 模拟完成: "
            f"初始资金={config.initial_capital:.2f}, "
            f"最终权益={summary.get('final_equity', 0):.2f}, "
            f"总收益={summary.get('total_return', 0):.2%}"
        )

        return summary

    def _handle_trigger_event(
        self,
        event: Event,
        account: Account,
        allocation_strategy: AllocationStrategy,
        completed_opportunities_map: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """处理 trigger 事件（开仓）"""
        stock_id = event.stock_id
        opportunity = event.opportunity or {}
        opp_id = str(opportunity.get("opportunity_id", "")).strip()
        trigger_price = float(opportunity.get("trigger_price", 0.0) or 0.0)

        if not stock_id or not opp_id or trigger_price <= 0:
            return None

        # 钩子：触发事件处理前，允许用户修改 event
        if self.hooks_dispatcher is not None:
            modified_event = self.hooks_dispatcher.call_hook(
                "on_capital_allocation_before_trigger_event",
                event,
                account,
                allocation_strategy,
            )
            if isinstance(modified_event, Event):
                event = modified_event
                stock_id = event.stock_id
                opportunity = event.opportunity or {}
                opp_id = str(opportunity.get("opportunity_id", "")).strip()
                trigger_price = float(opportunity.get("trigger_price", 0.0) or 0.0)
                if not stock_id or not opp_id or trigger_price <= 0:
                    return None

        # 检查是否已有持仓
        if account.has_position(stock_id):
            return None  # 跳过，同一只股票只能有一笔持仓

        # 检查组合持仓数是否已满
        if account.get_portfolio_size() >= allocation_strategy.max_portfolio_size:
            return None  # 组合已满

        # 计算 Kelly 模式的胜率（如果需要）
        win_rate = None
        if allocation_strategy.mode == "kelly":
            win_rate = self._calculate_win_rate(completed_opportunities_map)

        # 计算应该买入的股数
        buy_shares = allocation_strategy.calculate_shares_to_buy(
            account, trigger_price, win_rate
        )

        # 钩子：允许用户自定义买入股数
        if self.hooks_dispatcher is not None and buy_shares != 0:
            custom_shares = self.hooks_dispatcher.call_hook(
                "on_capital_allocation_calculate_shares_to_buy",
                event,
                account,
                allocation_strategy,
                buy_shares,
            )
            if isinstance(custom_shares, int) and custom_shares >= 0:
                buy_shares = custom_shares

        if buy_shares == 0:
            return None  # 无法买入（资金不足等）

        # 执行买入
        gross_amount = buy_shares * trigger_price
        fees = allocation_strategy.fee_calculator.calculate_fees(gross_amount, "buy")
        total_cost = gross_amount + fees

        if account.cash < total_cost:
            return None  # 现金不足

        # 更新账户
        account.cash -= total_cost

        # 更新或创建持仓
        position = account.positions.get(stock_id)
        if position is None:
            position = Position(stock_id=stock_id)
            account.positions[stock_id] = position

        position.shares = buy_shares
        position.avg_cost = total_cost / buy_shares
        position.current_opportunity_id = opp_id

        # 记录交易
        trade = {
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

        # 钩子：触发事件处理后，允许用户修改 trade
        if self.hooks_dispatcher is not None:
            modified_trade = self.hooks_dispatcher.call_hook(
                "on_capital_allocation_after_trigger_event",
                event,
                trade,
                account,
                allocation_strategy,
            )
            if isinstance(modified_trade, dict):
                trade = modified_trade

        return trade

    def _handle_target_event(
        self,
        event: Event,
        account: Account,
        fee_calculator: FeeCalculator,
    ) -> Optional[Dict[str, Any]]:
        """处理 target 事件（平仓）"""
        stock_id = event.stock_id
        target = event.target or {}
        opp_id = str(target.get("opportunity_id", "")).strip()
        target_price = float(target.get("price", 0.0) or 0.0)
        sell_ratio = float(target.get("sell_ratio", 0.0) or 0.0)

        if not stock_id or not opp_id or target_price <= 0 or sell_ratio <= 0:
            return None

        # 钩子：目标事件处理前，允许用户修改 event
        if self.hooks_dispatcher is not None:
            modified_event = self.hooks_dispatcher.call_hook(
                "on_capital_allocation_before_target_event",
                event,
                account,
                fee_calculator,
            )
            if isinstance(modified_event, Event):
                event = modified_event
                stock_id = event.stock_id
                target = event.target or {}
                opp_id = str(target.get("opportunity_id", "")).strip()
                target_price = float(target.get("price", 0.0) or 0.0)
                sell_ratio = float(target.get("sell_ratio", 0.0) or 0.0)
                if not stock_id or not opp_id or target_price <= 0 or sell_ratio <= 0:
                    return None

        # 检查持仓
        position = account.get_position(stock_id)
        if not position or position.shares == 0:
            return None  # 没有持仓

        # 检查机会 ID 是否匹配
        if position.current_opportunity_id != opp_id:
            return None  # 持仓对应的机会 ID 不匹配

        # 计算卖出股数
        sell_shares = int(position.shares * sell_ratio)

        # 钩子：允许用户自定义卖出股数
        if self.hooks_dispatcher is not None and sell_shares > 0:
            custom_sell = self.hooks_dispatcher.call_hook(
                "on_capital_allocation_calculate_shares_to_sell",
                event,
                position,
                fee_calculator,
                sell_shares,
            )
            if isinstance(custom_sell, int) and 0 <= custom_sell <= position.shares:
                sell_shares = custom_sell

        if sell_shares == 0:
            return None

        # 执行卖出
        gross_amount = sell_shares * target_price
        fees = fee_calculator.calculate_fees(gross_amount, "sell")
        net_proceeds = gross_amount - fees

        # 计算盈亏
        cost = sell_shares * position.avg_cost
        pnl = net_proceeds - cost

        # 更新账户
        account.cash += net_proceeds
        position.shares -= sell_shares
        position.realized_pnl += pnl

        # 如果全部卖出，清空持仓
        if position.shares == 0:
            position.current_opportunity_id = None

        # 记录交易
        trade = {
            "date": event.date,
            "stock_id": stock_id,
            "opportunity_id": opp_id,
            "side": "sell",
            "shares": sell_shares,
            "price": target_price,
            "amount": gross_amount,
            "fees": fees,
            "net_proceeds": net_proceeds,
            "pnl": pnl,
            "cash_after": account.cash,
            "equity_after": account.get_equity({stock_id: target_price}),
        }

        # 钩子：目标事件处理后，允许用户修改 trade
        if self.hooks_dispatcher is not None:
            modified_trade = self.hooks_dispatcher.call_hook(
                "on_capital_allocation_after_target_event",
                event,
                trade,
                account,
                fee_calculator,
            )
            if isinstance(modified_trade, dict):
                trade = modified_trade

        return trade

    def _calculate_win_rate(self, completed_opportunities_map: Dict[str, Dict[str, Any]]) -> float:
        """计算胜率（用于 Kelly 模式）"""
        if not completed_opportunities_map:
            return 0.5  # 默认 50%

        opportunities = list(completed_opportunities_map.values())
        win_count = sum(1 for opp in opportunities if float(opp.get("roi", 0) or 0) > 0)
        return win_count / len(opportunities) if opportunities else 0.5

    def _update_completed_opportunities(
        self,
        event: Event,
        completed_opportunities_map: Dict[str, Dict[str, Any]],
        account: Account,
    ) -> None:
        """更新已完成机会列表（用于 Kelly 模式）"""
        target = event.target or {}
        opp_id = str(target.get("opportunity_id", "")).strip()
        stock_id = event.stock_id

        if not opp_id:
            return

        # 检查是否完全平仓
        position = account.get_position(stock_id)
        if position and position.current_opportunity_id == opp_id and position.shares == 0:
            # 机会已完全结束，添加到已完成列表
            opportunity = event.opportunity or {}
            if opportunity and opp_id not in completed_opportunities_map:
                completed_opportunities_map[opp_id] = opportunity

    def _get_stock_prices_for_date(
        self, account: Account, price_source: Dict[str, Any]
    ) -> Dict[str, float]:
        """获取指定日期的股票价格（用于计算权益）"""
        stock_prices = {}
        for stock_id, position in account.positions.items():
            if position.shares > 0:
                # 使用持仓成本价作为当前价格（简化处理）
                stock_prices[stock_id] = position.avg_cost
        return stock_prices

    def _calculate_summary(
        self,
        account: Account,
        trades: List[Dict[str, Any]],
        equity_curve: List[Dict[str, Any]],
        initial_capital: float,
    ) -> Dict[str, Any]:
        """计算汇总统计"""
        # 计算最终权益
        final_equity = equity_curve[-1].get("equity", account.cash) if equity_curve else account.cash

        # 计算总收益
        total_return = (final_equity - initial_capital) / initial_capital if initial_capital > 0 else 0.0

        # 计算最大回撤
        max_drawdown = 0.0
        if equity_curve:
            peak = initial_capital
            for point in equity_curve:
                equity = point.get("equity", initial_capital)
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak if peak > 0 else 0.0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        # 统计交易
        buy_trades = [t for t in trades if t.get("side") == "buy"]
        sell_trades = [t for t in trades if t.get("side") == "sell"]
        win_trades = [t for t in sell_trades if t.get("pnl", 0) > 0]
        loss_trades = [t for t in sell_trades if t.get("pnl", 0) < 0]

        # 按股票汇总
        stock_summary = defaultdict(lambda: {
            "trade_count": 0,
            "total_pnl": 0.0,
            "win_trades": 0,
            "loss_trades": 0,
        })
        for trade in sell_trades:
            stock_id = trade.get("stock_id", "")
            stock_summary[stock_id]["trade_count"] += 1
            stock_summary[stock_id]["total_pnl"] += trade.get("pnl", 0.0)
            if trade.get("pnl", 0) > 0:
                stock_summary[stock_id]["win_trades"] += 1
            else:
                stock_summary[stock_id]["loss_trades"] += 1

        return {
            "initial_capital": initial_capital,
            "final_cash": account.cash,
            "final_equity": final_equity,
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "total_trades": len(trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "win_trades": len(win_trades),
            "loss_trades": len(loss_trades),
            "win_rate": len(win_trades) / len(sell_trades) if sell_trades else 0.0,
            "total_pnl": sum(t.get("pnl", 0.0) for t in sell_trades),
            "stock_summary": dict(stock_summary),
        }

    def _save_results(
        self,
        sim_version_dir: Path,
        sim_version_id: int,
        sot_version: str,
        trades: List[Dict[str, Any]],
        equity_curve: List[Dict[str, Any]],
        summary: Dict[str, Any],
        config: CapitalAllocationSimulatorConfig,
        settings_snapshot: Dict[str, Any],
    ) -> None:
        """保存模拟结果"""
        path_mgr = ResultPathManager(sim_version_dir=sim_version_dir)

        # 保存交易记录
        if config.save_trades:
            trades_path = path_mgr.trades_path()
            with trades_path.open("w", encoding="utf-8") as f:
                json.dump(trades, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

        # 保存权益曲线
        if config.save_equity_curve:
            equity_path = path_mgr.equity_timeseries_path()
            with equity_path.open("w", encoding="utf-8") as f:
                json.dump(equity_curve, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

        # 保存汇总
        summary_path = path_mgr.strategy_summary_path()
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

        # 保存 metadata
        metadata = {
            "sim_version": f"{sim_version_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "sot_version": sot_version,
            "config": config.__dict__,
            "settings_snapshot": settings_snapshot,
            "created_at": datetime.now().isoformat(),
        }
        metadata_path = path_mgr.metadata_path()
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

