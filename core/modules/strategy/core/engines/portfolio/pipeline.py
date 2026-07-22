"""Portfolio Pipeline — 资金/组合回放（无 BacktestEngine）。

主流程::

    1. load_enum_data            — 读 enum version runtime + entity_ids
    2. load_portfolio_settings   — 读 settings.portfolio
    3. begin_report              — 分配 portfolio version，写最小 runtime
    4. build_events              — enum investments → PortfolioEvent + Opportunity 索引
    5. simulate                  — on_pick_portfolio_member 选仓 → 账户事件回放
    6. finalize                  — overall / trades / equity 落盘 + 可缓存 report

边界:
    - 负责: 进程内编排（读 enum、settings、分配产物目录、选仓钩子、sizing、回放）
    - 不负责: BacktestEngine 调度、指纹缓存（Facade）、legacy capital 路径
    - 调用方: Strategy._run_steps（cache miss 之后）

与 legacy 差异:
    - 买入用 entry_price_raw（buy_price_model 对应 raw 字段，默认 next_open→raw open；
      不用 raw close 定仓；卖出不用 exit_price_raw）
    - profit = sell share value − purchase share value（Trade.share_value_profit）
    - on_pick_portfolio_member：Investment/InvestmentRow.to_opportunity 屏蔽结果字段；
      默认 EntrySelector（顺序 + max_portfolio_size 剩余槽位）；不返回仓位 sizing
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.infra.project_context import ProjectContext
from core.modules.market_profile.core.markets import create_market_rules
from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
    StockInvestments,
)
from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import PortfolioEvent
from core.modules.strategy.core.engines.portfolio.enter_selection import (
    EnterSelection,
    EntrySelector,
)
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.portfolio.report_writer import (
    PortfolioReportWriter,
)
from core.modules.strategy.core.engines.portfolio.simulator import (
    PortfolioSimResult,
    PortfolioSimulator,
)
from core.modules.strategy.core.engines.price_factor.enum_data import (
    EnumVersionData,
    load_enum_version,
    resolve_enum_version_dir,
)
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    PortfolioSettings,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings import (
    SkipInvestmentWhen,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)
from core.system import get_version

if TYPE_CHECKING:
    from core.modules.strategy.strategy import SimulateRuntimeContext

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
    def run(cls, ctx: "SimulateRuntimeContext") -> Dict[str, Any]:
        return cls.run_by_steps(ctx)

    @classmethod
    def run_by_steps(cls, ctx: "SimulateRuntimeContext") -> Dict[str, Any]:
        """按步骤串起选仓 → 回放 → 落盘，返回可缓存 report。"""
        data = cls.load_enum_data(ctx)
        portfolio_settings = cls.load_portfolio_settings(ctx)
        report = cls.begin_report(ctx, data, settings=portfolio_settings)
        strategy_settings = cls._strategy_settings(ctx)
        events, opportunities = cls.build_events(
            data,
            settings=portfolio_settings,
            skip_investment_when=strategy_settings.simulation.skip_investment_when,
        )
        sim_result = cls.simulate(
            events,
            opportunities,
            settings=portfolio_settings,
            report=report,
            ctx=ctx,
        )
        return cls.finalize(
            report,
            sim_result,
            data=data,
            settings=portfolio_settings,
        )

    @classmethod
    def load_enum_data(cls, ctx: "SimulateRuntimeContext") -> EnumVersionData:
        """解析 enum version 目录，加载 runtime + entity_ids（不读 CSV）。"""
        if ctx.enum_version is None or not str(ctx.enum_version).strip():
            raise ValueError("SimulateRuntimeContext.enum_version 不能为空")
        version_id = str(ctx.enum_version).strip()
        output_dir = resolve_enum_version_dir(ctx.strategy_key, version_id)
        return load_enum_version(output_dir, version_id)

    @classmethod
    def load_portfolio_settings(cls, ctx: "SimulateRuntimeContext") -> PortfolioSettings:
        """从 fingerprint 有效 settings 读取 ``portfolio`` 块。"""
        effective = ctx.effective_settings
        if effective is None:
            raise ValueError("SimulateRuntimeContext.effective_settings 不能为空")
        return effective.portfolio

    @classmethod
    def begin_report(
        cls,
        ctx: "SimulateRuntimeContext",
        data: EnumVersionData,
        *,
        settings: PortfolioSettings,
    ) -> PortfolioReportHandle:
        """分配 ``simulations/portfolio/{strategy}/{version}``，写最小 runtime。"""
        _ = settings
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
        data: EnumVersionData,
        *,
        settings: PortfolioSettings,
        skip_investment_when: Optional[SkipInvestmentWhen] = None,
    ) -> Tuple[List[PortfolioEvent], Dict[str, Opportunity]]:
        """读 enum CSV → 事件列表 + 已屏蔽结果字段的 Opportunity 索引。

        买入价固定为 ``entry_price_raw``；缺 raw 的行跳过（不回退 qfq）。
        ``skip_investment_when`` 命中触发日状态的行不生成事件（枚举 CSV 仍在）。
        """
        _ = settings
        policy = skip_investment_when or SkipInvestmentWhen(())
        entity_ids = list(data.entity_ids) or StockInvestments.collect_entity_ids(
            data.output_dir
        )
        events: List[PortfolioEvent] = []
        opportunities: Dict[str, Opportunity] = {}
        for entity_id in entity_ids:
            eid = str(entity_id or "").strip()
            if not eid:
                continue
            path = StockInvestments.file_path(data.output_dir, eid)
            if not path.is_file():
                continue
            loaded = StockInvestments.load(data.output_dir, eid)
            for row in loaded.rows:
                if policy.match_reason(row.stock_status_at_trigger):
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
        settings: PortfolioSettings,
        report: PortfolioReportHandle,
        ctx: "SimulateRuntimeContext",
    ) -> PortfolioSimResult:
        """选仓钩子过滤事件后做账户回放。"""
        strategy_settings = cls._strategy_settings(ctx)
        hook_runtime = cls._load_hook_runtime(ctx, strategy_settings)
        filtered = EnterSelection.create(
            settings=strategy_settings,
            strategy_name=str(ctx.strategy_key or report.strategy_key or ""),
            hook_runtime=hook_runtime,
            selector=EntrySelector.from_portfolio_settings(settings),
        ).apply(events, opportunities)

        fee_calculator = FeeCalculator.from_fees_config(settings.fees_config())
        market_rules = create_market_rules(report.market_profile)
        allocation = AllocationStrategy.create(
            portfolio=settings,
            market_rules=market_rules,
            fee_calculator=fee_calculator,
        )
        return PortfolioSimulator.create(
            allocation=allocation,
            fee_calculator=fee_calculator,
            save_equity_curve=bool(settings.output.save_equity_curve),
        ).run(filtered, initial_capital=float(settings.initial_capital))

    @classmethod
    def finalize(
        cls,
        report: PortfolioReportHandle,
        sim_result: PortfolioSimResult,
        *,
        data: EnumVersionData,
        settings: PortfolioSettings,
    ) -> Dict[str, Any]:
        """落盘 overall / trades / equity，返回可缓存 report dict。"""
        return PortfolioReportWriter(
            output_dir=report.output_dir,
            strategy_key=report.strategy_key,
            strategy_path=report.strategy_path,
            version_id=report.version_id,
            enum_version_id=report.enum_version_id,
        ).finalize(
            sim_result,
            period={"start_date": data.start_date, "end_date": data.end_date},
            save_trades=bool(settings.output.save_trades),
            save_equity_curve=bool(settings.output.save_equity_curve),
        )

    @classmethod
    def _strategy_settings(cls, ctx: "SimulateRuntimeContext") -> StrategySettings:
        effective = ctx.effective_settings
        if isinstance(effective, StrategySettings):
            return effective
        if effective is None:
            raise ValueError("SimulateRuntimeContext.effective_settings 不能为空")
        return StrategySettings.from_dict(dict(effective or {}))

    @classmethod
    def _load_hook_runtime(
        cls,
        ctx: "SimulateRuntimeContext",
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
