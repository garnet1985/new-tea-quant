"""单 entity 枚举 tracker：贯穿时间线跟踪 Investment（entity / slice 共用）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.data_class import (
    Investment,
    InvestmentTickInput,
    Opportunity,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


@dataclass
class EntityTracker:
    """单只股票（entity）在完整 calendar 上的枚举状态。

    边界:
    - 负责: Investment 注册 / tick / settle；recorded 供写 CSV
    - 不负责: 选股、数据加载、报告落盘
    - 调用方: EntityAdvancementHooks / SliceAdvancementHooks（entity / slice 共用）

    枚举产物是 **Investment**（模拟后的完整生命周期），不是裸 Opportunity。
    - ``active``：持仓中、尚未 complete 的 investment
    - ``recorded``：本 run 内全部 investment（含已完结）
    - ``extras``：策略可在时间线上累积的自定义数据
    """

    entity_id: str
    active: List[Investment] = field(default_factory=list)
    recorded: List[Investment] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)
    _investment_index: int = field(default=0, repr=False)

    def process_tick(self, tick: InvestmentTickInput) -> None:
        """推进一个 calendar step：对每个 active investment 调 ``tick``，complete 的移出 active。"""
        remaining: List[Investment] = []
        for investment in self.active:
            should_continue = investment.tick(tick)
            if should_continue:
                remaining.append(investment)
        self.active = remaining

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
    ) -> Investment:
        """Scan 命中：Opportunity → Investment，进入 active / recorded。"""
        self._investment_index += 1
        opportunity.bind_scan_context(
            strategy_name=strategy_name,
            stock_id=self.entity_id,
            stock_info=stock_info,
            trigger_date=trigger_date,
            trigger_price=trigger_price,
            opportunity_index=self._investment_index,
            market_profile=ProjectContext.config.get_default_market_profile_key(),
        )
        investment = Investment.create_from_opportunity(
            opportunity,
            settings=settings,
            open_dates=open_dates,
        )
        self.active.append(investment)
        self.recorded.append(investment)
        return investment

    def settle_incomplete(self, tick: InvestmentTickInput) -> None:
        """强制平仓：换仓日 / 模拟结束，对尚未 complete 的 active 调用 settle。"""
        for investment in list(self.active):
            investment.settle(tick)
        self.active.clear()

    def recorded_as_dicts(self) -> List[Dict[str, Any]]:
        """供 recorder 写 investments / goals CSV。"""
        return [inv.to_dict() for inv in self.recorded]


__all__ = ["EntityTracker"]
