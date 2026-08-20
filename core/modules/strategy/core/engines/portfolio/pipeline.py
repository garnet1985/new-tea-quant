"""Portfolio Pipeline — 资金/组合回放（无 BacktestEngine）。

本文件:
- PortfolioPipeline: enum → events → on_pick_portfolio_member → simulate → 落盘
  边界: 进程内事件流模拟；不用 BE / Timeline.drive（全局资金约束，无并行收益）
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.modules.market_profile import MarketRulesProxy
from core.modules.strategy.core.services.artifacts import EnumerateStore
from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import PortfolioEvent
from core.modules.strategy.core.engines.portfolio.enter_selection import (
    EnterSelection,
)
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.portfolio.report_manager import (
    ReportManager,
)
from core.modules.strategy.core.engines.portfolio.simulator import (
    PortfolioSimResult,
    PortfolioSimulator,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.progress import PipelineProgress

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession

_PROGRESS_PIPELINE = "portfolio"


class PortfolioPipeline:
    """资金/组合统一编排入口（无 BE）。"""

    @classmethod
    def run(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        return cls.run_by_steps(ctx)

    @classmethod
    def run_by_steps(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        """按步骤串起选仓 → 回放 → 落盘，返回可缓存 report。"""
        drive = PipelineProgress.drives_pipeline(_PROGRESS_PIPELINE)
        if drive:
            PipelineProgress.enter_step_bound("load")
        data = cls.load_enum_data(ctx)
        settings = cls._strategy_settings(ctx)
        report = cls.begin_report(ctx, data)
        if drive:
            PipelineProgress.complete_step_bound("load")
            PipelineProgress.enter_step_bound("dispatch")
        events, opportunities = cls.build_events(data, settings=settings)
        if drive:
            PipelineProgress.complete_step_bound("dispatch")
            PipelineProgress.enter_step_bound("execute")
            # No BE task ticks; mark execute mid-way before simulate returns.
            PipelineProgress.tick_execute_bound(0, 1)
        sim_result = cls.simulate(
            events,
            opportunities,
            settings=settings,
            report=report,
            ctx=ctx,
        )
        if drive:
            PipelineProgress.tick_execute_bound(1, 1)
            PipelineProgress.complete_step_bound("execute")
            PipelineProgress.enter_step_bound("report")
        out = cls.finalize(
            report,
            sim_result,
            data=data,
            settings=settings,
        )
        if drive:
            PipelineProgress.complete_step_bound("report")
        return out

    @classmethod
    def load_enum_data(cls, ctx: "SimulateSession") -> EnumerateStore:
        """解析 enum version 目录，加载 runtime + entity_ids（不读 CSV）。"""
        if ctx.enum_version is None or not str(ctx.enum_version).strip():
            raise ValueError("SimulateSession.enum_version 不能为空")
        version_id = str(ctx.enum_version).strip()
        return EnumerateStore.resolve(
            ctx.strategy_folder, version_id=version_id
        )

    @classmethod
    def begin_report(
        cls,
        ctx: "SimulateSession",
        data: EnumerateStore,
    ) -> ReportManager:
        """分配 portfolio version 目录并写 runtime。"""
        return ReportManager.begin(ctx, data)

    @classmethod
    def build_events(
        cls,
        data: EnumerateStore,
        *,
        settings: StrategySettings,
    ) -> Tuple[List[PortfolioEvent], Dict[str, Opportunity]]:
        """读 enum CSV → 事件列表 + 已屏蔽结果字段的 Opportunity 索引。

        买入价固定为 ``entry_price_raw``；缺 raw 的行跳过（不回退 qfq）。
        ``simulation.risk_control.should_skip_enter`` 命中触发日状态的行不生成事件。
        """
        control = settings.simulation.risk_control
        entity_ids = list(data.entity_ids) or data.list_investment_entities()
        events: List[PortfolioEvent] = []
        opportunities: Dict[str, Opportunity] = {}
        for entity_id in entity_ids:
            eid = str(entity_id or "").strip()
            if not eid:
                continue
            if not data.has_investments(eid):
                continue
            loaded = data.investments(eid)
            for row in loaded.rows:
                if control.should_skip_enter(status_tags=row.stock_status_at_trigger):
                    continue
                row_events = PortfolioEvent.from_investment_row(row, eid)
                if not row_events:
                    continue
                events.extend(row_events)
                oid = str(row.investment_id or "").strip()
                if oid:
                    key = f"{eid}:{oid}"
                    if key not in opportunities:
                        opp = row.to_opportunity(eid)
                        # 选仓索引用 entity:investment，避免跨股 id 碰撞
                        if opp.meta is not None:
                            opp.meta.opportunity_id = key
                        opportunities[key] = opp

        events.sort(
            key=lambda e: (
                str(e.date or ""),
                0 if e.is_buy() else 1,
                str(e.entity_id or ""),
                str(e.investment_id or ""),
            )
        )
        return events, opportunities

    @classmethod
    def simulate(
        cls,
        events: List[PortfolioEvent],
        opportunities: Dict[str, Opportunity],
        *,
        settings: StrategySettings,
        report: ReportManager,
        ctx: "SimulateSession",
    ) -> PortfolioSimResult:
        """选仓钩子过滤事件后做账户回放。"""
        hook_runtime = cls._load_hook_runtime(ctx, settings)
        filtered = EnterSelection.create(
            settings=settings,
            strategy_name=str(ctx.strategy_key or report.strategy_key or ""),
            hook_runtime=hook_runtime,
        ).apply(events, opportunities)

        fee_calculator = FeeCalculator.from_fees(settings)
        market_rules = MarketRulesProxy.for_market(report.market_profile)
        allocation = AllocationStrategy.create(
            settings=settings,
            market_rules=market_rules,
            fee_calculator=fee_calculator,
        )
        portfolio = settings.portfolio
        return PortfolioSimulator.create(
            allocation=allocation,
            fee_calculator=fee_calculator,
            save_equity_curve=bool(portfolio.output.save_equity_curve),
        ).run(filtered, initial_capital=float(portfolio.initial_capital))

    @classmethod
    def finalize(
        cls,
        report: ReportManager,
        sim_result: PortfolioSimResult,
        *,
        data: EnumerateStore,
        settings: StrategySettings,
    ) -> Dict[str, Any]:
        """落盘 overall / trades / equity，返回可缓存 report dict。"""
        portfolio = settings.portfolio
        return report.finalize(
            sim_result,
            period={"start_date": data.start_date, "end_date": data.end_date},
            save_trades=bool(portfolio.output.save_trades),
            save_equity_curve=bool(portfolio.output.save_equity_curve),
        )

    @classmethod
    def _strategy_settings(cls, ctx: "SimulateSession") -> StrategySettings:
        effective = ctx.effective_settings
        if isinstance(effective, StrategySettings):
            return effective
        if effective is None:
            raise ValueError("SimulateSession.effective_settings 不能为空")
        return StrategySettings.from_dict(dict(effective or {}))

    @classmethod
    def _load_hook_runtime(
        cls,
        ctx: "SimulateSession",
        strategy_settings: StrategySettings,
    ) -> Optional[StrategyHookRuntime]:
        runtime, err = StrategyHookRuntime.from_strategy_info(
            ctx.strategy_info,
            strategy_settings,
        )
        if err is not None:
            # 无 hooks 时走 EntrySelector 默认（EnterSelection）
            return None
        return runtime


__all__ = ["PortfolioPipeline"]
