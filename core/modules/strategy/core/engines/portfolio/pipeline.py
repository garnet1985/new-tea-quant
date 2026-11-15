"""Portfolio Pipeline — 资金/组合回放（无 BacktestEngine）。

本文件:
- PortfolioPipeline: enum → events → select_portfolio_entries → simulate → 落盘
  边界: 进程内事件流模拟；不用 BE / Timeline.drive（全局资金约束，无并行收益）
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from core.modules.market_profile import MarketRulesProxy
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResultsManager,
)
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
        sim_result = cls.simulate(
            events,
            opportunities,
            settings=settings,
            report=report,
            ctx=ctx,
        )
        if drive:
            PipelineProgress.complete_step_bound("execute")
            PipelineProgress.enter_step_bound("report")
        out = cls.finalize(
            report,
            sim_result,
            data=data,
            settings=settings,
        )
        # report 步由 Strategy._run_steps 在归因之后 complete
        return out

    @classmethod
    def load_enum_data(cls, ctx: "SimulateSession") -> EnumerateStore:
        """解析 enum version 目录，加载 runtime + entity_ids（不读枚举结果）。"""
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
        """从枚举结果展开买卖事件 + 选仓用 Opportunity（屏蔽 ROI / result）。

        买入扣现金用 ``entry_price_raw``；平仓用枚举 hfq ``weighted_roi``。
        缺合法买入 raw 的笔跳过。不要求 ``exit_price_raw``，也不用它算钱。
        ``simulation.risk_control.should_skip_enter`` 命中触发日状态的行不生成事件。
        """
        control = settings.simulation.risk_control
        manager = EnumResultsManager.at(data.output_dir)
        entity_ids = [
            str(item or "").strip()
            for item in (data.entity_ids or [])
            if str(item or "").strip()
        ]
        if not entity_ids:
            entity_ids = manager.list_entities() or data.list_investment_entities()
        events: List[PortfolioEvent] = []
        opportunities: Dict[str, Opportunity] = {}
        for entity_id in entity_ids:
            eid = str(entity_id or "").strip()
            if not eid:
                continue
            for row in manager.results(eid):
                filled = row.with_entity_id(eid) if eid and not row.entity_id else row
                if control.should_skip_enter(status_tags=filled.stock_status_at_trigger):
                    continue
                row_events = PortfolioEvent.from_enum_result(filled, eid)
                if not row_events:
                    continue
                events.extend(row_events)
                oid = str(filled.investment_id or "").strip()
                if not oid:
                    continue
                key = f"{eid}:{oid}"
                if key in opportunities:
                    continue
                opp = filled.to_opportunity()
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
        """选仓钩子过滤事件后做账户回放。

        进度（execute）：选仓按交易日、回放按交易日，拼成一条 ``done/total``。
        选仓阶段 total 只用「选仓日数」（不再混入事件条数，避免出现 1/96020）。
        """
        drive = PipelineProgress.drives_pipeline(_PROGRESS_PIPELINE)
        select_dates = sorted(
            {
                str(e.date or "").strip()
                for e in events
                if str(e.date or "").strip()
            }
        )
        n_select = max(len(select_dates), 1)
        # 选仓占进度轴前半（预留回放）；UI 计数器用真实选仓日 done/n_select
        total_select_phase = 2 * n_select
        progress_state = {"last_emit_done": -1}

        def emit(
            done: int,
            total: int,
            description: str,
            *,
            force: bool = False,
            counter_done: Optional[int] = None,
            counter_total: Optional[int] = None,
        ) -> None:
            if not drive:
                return
            t = max(int(total), 1)
            d = max(0, min(int(done), t))
            # 最多约 200 次落盘；首尾与 force 必写
            step = max(1, t // 200)
            if (
                not force
                and d not in (0, 1, t)
                and d - progress_state["last_emit_done"] < step
            ):
                return
            progress_state["last_emit_done"] = d
            PipelineProgress.tick_execute_bound(
                d,
                t,
                description=str(description or "").strip() or None,
                counter_done=counter_done,
                counter_total=counter_total,
            )

        def on_select(done: int, phase_total: int, description: str) -> None:
            pt = max(int(phase_total), 1)
            emit(
                done,
                total_select_phase,
                description,
                counter_done=done,
                counter_total=pt,
            )

        hook_runtime = cls._load_hook_runtime(ctx, settings)
        filtered = EnterSelection.create(
            settings=settings,
            strategy_name=str(ctx.strategy_key or report.strategy_key or ""),
            hook_runtime=hook_runtime,
        ).apply(
            events,
            opportunities,
            on_progress=on_select if drive else None,
        )

        sim_dates: List[str] = []
        seen_sim: Set[str] = set()
        for event in filtered:
            d = str(event.date or "").strip()
            if d and d not in seen_sim:
                seen_sim.add(d)
                sim_dates.append(d)
        n_sim = max(len(sim_dates), 1)
        total_run = n_select + n_sim
        # 切入回放：换 total；选仓已完成 n_select / total_run
        progress_state["last_emit_done"] = -1
        emit(
            n_select,
            total_run,
            "回放",
            force=True,
            counter_done=0,
            counter_total=n_sim,
        )

        def on_sim(done: int, phase_total: int, description: str) -> None:
            pt = max(int(phase_total), 1)
            emit(
                n_select + done,
                total_run,
                description,
                counter_done=done,
                counter_total=pt,
            )

        fee_calculator = FeeCalculator.from_fees(settings)
        market_rules = MarketRulesProxy.for_market(report.market_profile)
        allocation = AllocationStrategy.create(
            settings=settings,
            market_rules=market_rules,
            fee_calculator=fee_calculator,
        )
        portfolio = settings.portfolio
        result = PortfolioSimulator.create(
            allocation=allocation,
            fee_calculator=fee_calculator,
            save_equity_curve=bool(portfolio.output.save_equity_curve),
        ).run(
            filtered,
            initial_capital=float(portfolio.initial_capital),
            on_progress=on_sim if drive else None,
        )
        emit(total_run, total_run, "回测中", force=True)
        return result

    @classmethod
    def finalize(
        cls,
        report: ReportManager,
        sim_result: PortfolioSimResult,
        *,
        data: EnumerateStore,
        settings: StrategySettings,
    ) -> Dict[str, Any]:
        """落盘 overall / trades / equity，返回可缓存 report dict。

盯市在 ``ReportManager.finalize`` 内、写报告之前完成。
"""
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
