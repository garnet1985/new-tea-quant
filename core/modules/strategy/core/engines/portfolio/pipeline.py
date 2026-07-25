"""Portfolio Pipeline — 资金/组合回放（无 BacktestEngine）。

本文件:
- PortfolioPipeline: enum → events → on_pick_portfolio_member → simulate → 落盘
  边界: 进程内事件流模拟；不用 BE / Timeline.drive（全局资金约束，无并行收益）
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.infra.project_context import ProjectContext
from core.modules.market_profile.core.markets import create_market_rules
from core.modules.strategy.core.engines.portfolio.enum_input.investments import (
    EntityInvestmentCsv,
)
from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import PortfolioEvent
from core.modules.strategy.core.engines.portfolio.enter_selection import (
    EnterSelection,
)
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.portfolio.report_writer import (
    PortfolioReportWriter,
)
from core.modules.strategy.core.engines.portfolio.simulator import (
    PortfolioSimResult,
    PortfolioSimulator,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.enum_source import EnumSource
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)
from core.system import get_version

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession

_RUNTIME_ENV_FILE = "0_runtime_env.json"
_DEFAULT_MARKET_PROFILE = "china_a_stock"


@dataclass
class PortfolioReportHandle:
    """本轮 run 的产物句柄（最小版；完整 ReportManager 后续补）。"""

    output_dir: Path
    strategy_key: str
    strategy_path: str
    version_id: int
    enum_version_id: str
    market_profile: str = _DEFAULT_MARKET_PROFILE


class PortfolioPipeline:
    """资金/组合统一编排入口（无 BE）。"""

    @classmethod
    def run(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        return cls.run_by_steps(ctx)

    @classmethod
    def run_by_steps(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        """按步骤串起选仓 → 回放 → 落盘，返回可缓存 report。"""
        data = cls.load_enum_data(ctx)
        settings = cls._strategy_settings(ctx)
        report = cls.begin_report(ctx, data)
        events, opportunities = cls.build_events(data, settings=settings)
        sim_result = cls.simulate(
            events,
            opportunities,
            settings=settings,
            report=report,
            ctx=ctx,
        )
        return cls.finalize(
            report,
            sim_result,
            data=data,
            settings=settings,
        )

    @classmethod
    def load_enum_data(cls, ctx: "SimulateSession") -> EnumSource:
        """解析 enum version 目录，加载 runtime + entity_ids（不读 CSV）。"""
        if ctx.enum_version is None or not str(ctx.enum_version).strip():
            raise ValueError("SimulateSession.enum_version 不能为空")
        version_id = str(ctx.enum_version).strip()
        output_dir = EnumSource.resolve_dir(ctx.strategy_key, version_id)
        return EnumSource.load(output_dir, version_id)

    @classmethod
    def begin_report(
        cls,
        ctx: "SimulateSession",
        data: EnumSource,
    ) -> PortfolioReportHandle:
        """分配 ``simulations/portfolio/{strategy}/{version}``，写最小 runtime。"""
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
            "market_profile": (
                str(data.runtime.market_profile or "").strip() or _DEFAULT_MARKET_PROFILE
            ),
            "engine_version": get_version(),
            "created_at": datetime.now().isoformat(),
            "kind": "portfolio",
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / _RUNTIME_ENV_FILE).write_text(
            json.dumps(runtime, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        market_profile = (
            str(data.runtime.market_profile or "").strip() or _DEFAULT_MARKET_PROFILE
        )
        return PortfolioReportHandle(
            output_dir=output_dir,
            strategy_key=strategy_key or strategy_path,
            strategy_path=strategy_path,
            version_id=int(version_id),
            enum_version_id=str(data.version_id),
            market_profile=market_profile,
        )

    @classmethod
    def build_events(
        cls,
        data: EnumSource,
        *,
        settings: StrategySettings,
    ) -> Tuple[List[PortfolioEvent], Dict[str, Opportunity]]:
        """读 enum CSV → 事件列表 + 已屏蔽结果字段的 Opportunity 索引。

        买入价固定为 ``entry_price_raw``；缺 raw 的行跳过（不回退 qfq）。
        ``simulation.risk_control.should_skip_enter`` 命中触发日状态的行不生成事件（枚举 CSV 仍在）。
        """
        control = settings.simulation.risk_control
        entity_ids = list(data.entity_ids) or EntityInvestmentCsv.collect_entity_ids(
            data.output_dir
        )
        events: List[PortfolioEvent] = []
        opportunities: Dict[str, Opportunity] = {}
        for entity_id in entity_ids:
            eid = str(entity_id or "").strip()
            if not eid:
                continue
            path = EntityInvestmentCsv.file_path(data.output_dir, eid)
            if not path.is_file():
                continue
            loaded = EntityInvestmentCsv.load(data.output_dir, eid)
            for row in loaded.rows:
                if control.should_skip_enter(status_tags=row.stock_status_at_trigger):
                    continue
                row_events = PortfolioEvent.from_investment_row(row, eid)
                if not row_events:
                    continue
                events.extend(row_events)
                oid = str(row.investment_id or "").strip()
                if oid and oid not in opportunities:
                    opportunities[oid] = row.to_opportunity(eid)

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
        report: PortfolioReportHandle,
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
        market_rules = create_market_rules(report.market_profile)
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
        report: PortfolioReportHandle,
        sim_result: PortfolioSimResult,
        *,
        data: EnumSource,
        settings: StrategySettings,
    ) -> Dict[str, Any]:
        """落盘 overall / trades / equity，返回可缓存 report dict。"""
        portfolio = settings.portfolio
        return PortfolioReportWriter(
            output_dir=report.output_dir,
            strategy_key=report.strategy_key,
            strategy_path=report.strategy_path,
            version_id=report.version_id,
            enum_version_id=report.enum_version_id,
        ).finalize(
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


__all__ = ["PortfolioPipeline", "PortfolioReportHandle"]
