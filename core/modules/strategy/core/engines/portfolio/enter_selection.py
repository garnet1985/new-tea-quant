"""Portfolio 入场挑选与 ``on_pick_portfolio_member`` 编排。

本文件:
- EntrySelector: 按 max_portfolio_size + 顺序选 Opportunity（不算 sizing）
- EnterSelection: 钩子 / 跨日 held 容量 / 事件过滤编排
  边界: 负责「选谁进组合」；不负责股数计算（AllocationStrategy）或账户回放
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set

from core.modules.strategy.core.engines.portfolio.data_class import PortfolioEvent
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.context import DataContext
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime


@dataclass(frozen=True)
class EntrySelector:
    """按配置挑选当日要进入组合的机会（只选谁，不算买多少）。

    不含仓位 sizing（equal_capital / equal_shares / kelly）；那是 AllocationStrategy 的事。
    """

    max_portfolio_size: int

    @classmethod
    def from_strategy_settings(cls, settings: StrategySettings) -> "EntrySelector":
        size = int(settings.portfolio.allocation.max_portfolio_size or 0)
        if size <= 0:
            raise ValueError("max_portfolio_size 必须 > 0")
        return cls(max_portfolio_size=size)

    @staticmethod
    def opportunity_id(opportunity: Opportunity) -> str:
        return str(getattr(opportunity.meta, "opportunity_id", "") or "").strip()

    @staticmethod
    def entity_id(opportunity: Opportunity) -> str:
        stock = getattr(opportunity, "stock", None)
        if stock is None:
            return ""
        return str(getattr(stock, "id", "") or "").strip()

    def remaining_slots(self, held_entity_ids: Set[str]) -> int:
        held = {str(x or "").strip() for x in held_entity_ids if str(x or "").strip()}
        return max(0, int(self.max_portfolio_size) - len(held))

    def pick(
        self,
        available: Sequence[Opportunity],
        *,
        held_entity_ids: Optional[Set[str]] = None,
    ) -> List[Opportunity]:
        """按 ``available`` 顺序挑选；跳过已持仓 entity；至多填满剩余槽位。"""
        held = {
            str(x or "").strip()
            for x in (held_entity_ids or set())
            if str(x or "").strip()
        }
        remaining = self.remaining_slots(held)
        if remaining <= 0:
            return []

        picked: List[Opportunity] = []
        seen_entities = set(held)
        for opp in available or []:
            if remaining <= 0:
                break
            eid = self.entity_id(opp)
            oid = self.opportunity_id(opp)
            if not oid:
                continue
            if eid and eid in seen_entities:
                continue
            picked.append(opp)
            if eid:
                seen_entities.add(eid)
            remaining -= 1
        return picked

    def pick_ids(
        self,
        available: Sequence[Opportunity],
        *,
        held_entity_ids: Optional[Set[str]] = None,
    ) -> List[str]:
        return [
            self.opportunity_id(opp)
            for opp in self.pick(available, held_entity_ids=held_entity_ids)
            if self.opportunity_id(opp)
        ]

    def account_snapshot(self, held_entity_ids: Set[str]) -> Dict[str, Any]:
        """供钩子 ctx['account'] 使用的容量快照。"""
        held = sorted(
            str(x or "").strip() for x in held_entity_ids if str(x or "").strip()
        )
        return {
            "max_portfolio_size": int(self.max_portfolio_size),
            "open_position_count": len(held),
            "held_entity_ids": held,
            "remaining_slots": self.remaining_slots(set(held)),
        }


@dataclass
class EnterSelection:
    """``on_pick_portfolio_member`` 编排：按日选仓并过滤事件。"""

    settings: StrategySettings
    strategy_name: str
    selector: EntrySelector
    hook_runtime: Optional[StrategyHookRuntime] = None

    @classmethod
    def create(
        cls,
        *,
        settings: StrategySettings,
        strategy_name: str,
        hook_runtime: Optional[StrategyHookRuntime] = None,
        selector: Optional[EntrySelector] = None,
    ) -> "EnterSelection":
        return cls(
            settings=settings,
            strategy_name=str(strategy_name or ""),
            selector=selector or EntrySelector.from_strategy_settings(settings),
            hook_runtime=hook_runtime,
        )

    @staticmethod
    def normalize_selected_ids(
        available: Sequence[Opportunity],
        selected: Optional[Sequence[Any]],
    ) -> List[str]:
        """将钩子返回值规范为 opportunity_id 列表（仅保留当日 available 内的 id）。"""
        available_ids = {
            EntrySelector.opportunity_id(opp)
            for opp in available
            if EntrySelector.opportunity_id(opp)
        }
        out: List[str] = []
        seen: Set[str] = set()
        for item in selected or []:
            oid = ""
            if isinstance(item, Opportunity):
                oid = EntrySelector.opportunity_id(item)
            elif isinstance(item, str):
                oid = item.strip()
            elif isinstance(item, dict):
                meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
                oid = str(
                    meta.get("opportunity_id") or item.get("opportunity_id") or ""
                ).strip()
            if not oid or oid not in available_ids or oid in seen:
                continue
            seen.add(oid)
            out.append(oid)
        return out

    @staticmethod
    def filter_events(
        events: Sequence[PortfolioEvent],
        selected_ids: Set[str],
    ) -> List[PortfolioEvent]:
        """只保留选中 investment 的 buy/sell 事件。"""
        keep = {str(x or "").strip() for x in selected_ids if str(x or "").strip()}
        return [
            event
            for event in events
            if str(event.investment_id or "").strip() in keep
        ]

    def select_for_date(
        self,
        *,
        date: str,
        available: Sequence[Opportunity],
        held_entity_ids: Set[str],
    ) -> List[str]:
        """挑选当日 members：用户 override 钩子，否则 ``EntrySelector``。"""
        opps = list(available or [])
        if not opps:
            return []

        snapshot = self.selector.account_snapshot(held_entity_ids)
        use_hook = (
            self.hook_runtime is not None
            and self.hook_runtime.is_overridden("on_pick_portfolio_member")
        )
        if use_hook:
            ctx = DataContext(
                strategy_name=self.strategy_name,
                settings=self.settings,
                base_data_key="",
            )
            ctx.data.update(
                {
                    "stock_list": [],
                    "now": str(date or "").strip(),
                    "opportunities": opps,
                    "account": snapshot,
                }
            )
            selected = self.hook_runtime.call("on_pick_portfolio_member", ctx)
            return self.normalize_selected_ids(opps, selected)

        return self.selector.pick_ids(opps, held_entity_ids=held_entity_ids)

    def apply(
        self,
        events: Sequence[PortfolioEvent],
        opportunities_by_id: Dict[str, Opportunity],
    ) -> List[PortfolioEvent]:
        """按日挑选 portfolio members，过滤未选中的 investment 事件。

        跨日维护持仓 entity：卖出释放槽位，买入占用槽位（近似 legacy 容量约束）。
        """
        dates = sorted(
            {
                str(e.date or "").strip()
                for e in events
                if str(e.date or "").strip()
            }
        )
        selected: Set[str] = set()
        held_entities: Set[str] = set()
        inv_entity: Dict[str, str] = {
            oid: EntrySelector.entity_id(opp)
            for oid, opp in opportunities_by_id.items()
            if oid and EntrySelector.entity_id(opp)
        }
        for event in events:
            oid = str(event.investment_id or "").strip()
            eid = str(event.entity_id or "").strip()
            if oid and eid:
                inv_entity.setdefault(oid, eid)

        for date in dates:
            for event in events:
                if str(event.date or "").strip() != date or not event.is_sell():
                    continue
                oid = str(event.investment_id or "").strip()
                if oid not in selected:
                    continue
                eid = inv_entity.get(oid) or str(event.entity_id or "").strip()
                if eid:
                    held_entities.discard(eid)

            day_buys = [
                e
                for e in events
                if e.is_buy() and str(e.date or "").strip() == date
            ]
            available: List[Opportunity] = []
            for buy in day_buys:
                oid = str(buy.investment_id or "").strip()
                opp = opportunities_by_id.get(oid)
                if opp is not None:
                    available.append(opp)

            picked_ids = self.select_for_date(
                date=date,
                available=available,
                held_entity_ids=held_entities,
            )
            for oid in picked_ids:
                selected.add(oid)
                eid = inv_entity.get(oid, "")
                if not eid:
                    opp = opportunities_by_id.get(oid)
                    if opp is not None:
                        eid = EntrySelector.entity_id(opp)
                if not eid:
                    for buy in day_buys:
                        if str(buy.investment_id or "").strip() == oid:
                            eid = str(buy.entity_id or "").strip()
                            break
                if eid:
                    held_entities.add(eid)
                    inv_entity[oid] = eid

        return self.filter_events(events, selected)


__all__ = [
    "EnterSelection",
    "EntrySelector",
]
