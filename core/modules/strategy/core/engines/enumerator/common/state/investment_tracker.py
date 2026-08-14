"""单 entity 上的 Investment 生命周期 tracker（entity / slice Executor 共用）。

调用链:
  BE Timeline.drive
    → JobExecutor.on_tick
    → EntityTaskState / SliceTaskState.on_calendar_day
    → InvestmentTracker.process_tick(as_of, bar)
         pending_exit.try_exit → pending_enter.try_enter → open.check_targets
    →（同日 scan 后）register_from_opportunity → 再 process_tick

本文件:
- InvestmentTracker: 分桶编排 Investment 生命周期反应
  边界: 负责单股时间线状态；不负责选股、数据加载或报告落盘
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.data_class import (
    Investment,
    Lifecycle,
    Opportunity,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


@dataclass
class InvestmentTracker:
    """单只股票（entity）在完整 calendar 上的枚举状态。

    边界:
    - 负责: 注册机会；按分桶调用 try_enter / check_targets / try_exit / settle
    - 不负责: 选股、数据加载、报告落盘
    - 调用方: EntityTaskState / SliceTaskState（entity / slice 共用）

    生命周期分桶:
    - ``pending_enter``：``PENDING_TO_ENTER``（条件未齐，如等次日 open）
    - ``open``：``OPEN``
    - ``pending_exit``：``PENDING_TO_EXIT``
    - ``completed``：``COMPLETE``
    """

    entity_id: str
    pending_enter: List[Investment] = field(default_factory=list)
    open: List[Investment] = field(default_factory=list)
    pending_exit: List[Investment] = field(default_factory=list)
    completed: List[Investment] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)
    _investment_index: int = field(default=0, repr=False)

    @property
    def has_live(self) -> bool:
        """仍有未完结 investment。"""
        return bool(self.pending_enter or self.open or self.pending_exit)

    def investment_count(self) -> int:
        return (
            len(self.pending_enter)
            + len(self.open)
            + len(self.pending_exit)
            + len(self.completed)
        )

    def process_tick(self, as_of: str, bar: Dict[str, Any]) -> None:
        """一个 calendar step：pending_exit → pending_enter → open。"""
        as_of = str(as_of or "").strip()
        next_pending_enter: List[Investment] = []
        next_open: List[Investment] = []
        next_pending_exit: List[Investment] = []

        for investment in self.pending_exit:
            investment.try_exit(as_of, bar)
            self._place_after_react(
                investment, next_pending_enter, next_open, next_pending_exit
            )

        for investment in self.pending_enter:
            investment.try_enter(as_of, bar)
            # 本 tick 刚入场 → 进 open，不跑 check_targets
            self._place_after_react(
                investment, next_pending_enter, next_open, next_pending_exit
            )

        for investment in self.open:
            investment.check_targets(as_of, bar)
            self._place_after_react(
                investment, next_pending_enter, next_open, next_pending_exit
            )

        self.pending_enter = next_pending_enter
        self.open = next_open
        self.pending_exit = next_pending_exit

    def _place_after_react(
        self,
        investment: Investment,
        next_pending_enter: List[Investment],
        next_open: List[Investment],
        next_pending_exit: List[Investment],
    ) -> None:
        life = investment.lifecycle
        if life == Lifecycle.COMPLETE:
            self.completed.append(investment)
        elif life == Lifecycle.PENDING_TO_ENTER:
            next_pending_enter.append(investment)
        elif life == Lifecycle.PENDING_TO_EXIT:
            next_pending_exit.append(investment)
        elif life == Lifecycle.OPEN:
            next_open.append(investment)
        else:
            next_open.append(investment)

    def register_from_opportunity(
        self,
        opportunity: Opportunity,
        *,
        settings: StrategySettings,
        open_dates: Sequence[str],
        strategy_name: str,
        stock_info: Dict[str, Any],
        trigger_date: str,
        trigger_price: float,
        trigger_price_raw: float = 0.0,
        status_tags_provider: Any = None,
    ) -> Investment:
        """Scan 命中：Opportunity → Investment（``PENDING_TO_ENTER``）→ ``pending_enter``。"""
        self._investment_index += 1
        opportunity.bind_scan_context(
            strategy_name=strategy_name,
            stock_id=self.entity_id,
            stock_info=stock_info,
            trigger_date=trigger_date,
            trigger_price=trigger_price,
            trigger_price_raw=trigger_price_raw,
            opportunity_index=self._investment_index,
            market_profile=ProjectContext.config.get_default_market_profile_key(),
        )
        investment = Investment.create_from_opportunity(
            opportunity,
            settings=settings,
            open_dates=open_dates,
            status_tags_provider=status_tags_provider,
        )
        self.pending_enter.append(investment)
        return investment

    def settle_incomplete(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        reason: str | None = None,
    ) -> None:
        """强制平仓：换仓日 / 模拟结束，对未完结分桶 settle → completed。

        ``reason`` 透传给 ``Investment.settle``；换仓传 ``period_end``，
        样本边界默认 ``simulate_end``。
        """
        as_of = str(as_of or "").strip()
        live = list(self.pending_enter) + list(self.open) + list(self.pending_exit)
        self.pending_enter.clear()
        self.open.clear()
        self.pending_exit.clear()
        for investment in live:
            investment.settle(as_of, bar, reason=reason)
            self.completed.append(investment)

    def investments_as_dicts(self) -> List[Dict[str, Any]]:
        """供 recorder 写 investments / goals CSV。"""
        return [
            inv.to_dict()
            for inv in (
                *self.pending_enter,
                *self.open,
                *self.pending_exit,
                *self.completed,
            )
        ]


__all__ = ["InvestmentTracker"]
