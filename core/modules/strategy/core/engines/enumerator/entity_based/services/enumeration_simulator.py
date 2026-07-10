"""entity_based 枚举模拟：calendar 驱动 + per-entity tracker。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.engines.enumerator.entity_based.state.entity_tracker import (
    EntityTracker,
)
from core.modules.strategy.core.engines.shared.data_class import Opportunity
from core.modules.strategy.core.engines.shared.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.context.data_context import DataContext

logger = logging.getLogger(__name__)


@dataclass
class EntityEnumerationSimulator:
    """在子进程内驱动「全局 calendar × 多 entity」枚举。

    每个 entity 独立 ``EntityTracker``；本类负责日循环与 hooks 调度。
    """

    entity_ids: List[str]
    trackers: Dict[str, EntityTracker] = field(init=False)
    _stock_info: Dict[str, Dict[str, Any]] = field(init=False, repr=False)
    _last_bar_by_entity: Dict[str, Dict[str, Any]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.trackers = {
            str(entity_id).strip(): EntityTracker(entity_id=str(entity_id).strip())
            for entity_id in self.entity_ids
            if str(entity_id).strip()
        }
        self._stock_info = {
            entity_id: StockMetaHelper.load(entity_id) for entity_id in self.trackers
        }
        self._last_bar_by_entity = {}

    def run(
        self,
        *,
        open_dates: List[str],
        start_date: str,
        end_date: str,
        settings: StrategySettings,
        hooks: Any,
        strategy_name: str,
        entity_contracts: Dict[str, Any],
        global_data: Dict[str, Any],
        entity_specified: List[Dict[str, Any]],
    ) -> Dict[str, EntityTracker]:
        settings_dict = settings.to_dict()
        resolver = StrategyDataResolver(settings_dict)
        base_data_key = str(resolver.base.get("data_key") or "").strip()
        if not base_data_key:
            raise ValueError("settings.data.base.data_key 不能为空")

        min_required = resolver.min_required_records
        max_holding_days = self._resolve_max_holding_days(settings_dict)
        calendar_dict = {
            "period_start": start_date,
            "period_end": end_date,
            "open_dates": open_dates,
        }
        filtered_dates = [
            day for day in open_dates if str(start_date) <= str(day) <= str(end_date)
        ]
        if not filtered_dates:
            logger.warning("无有效 open_dates：%s ~ %s", start_date, end_date)
            return self.trackers

        for now in filtered_dates:
            pit_data_by_entity = self._load_pit_by_entity(entity_contracts, now)

            for entity_item in entity_specified:
                entity_id = str(entity_item.get("id") or "").strip()
                tracker = self.trackers.get(entity_id)
                if tracker is None:
                    continue

                per_entity_pit = pit_data_by_entity.get(entity_id, {})
                bar = self._bar_on(
                    per_entity_pit,
                    base_data_key=base_data_key,
                    as_of=now,
                    min_required=min_required,
                )
                if bar is not None:
                    self._last_bar_by_entity[entity_id] = bar
                    tracker.process_as_of_date(
                        now,
                        bar,
                        open_dates=filtered_dates,
                        max_holding_days=max_holding_days,
                    )

                if bar is None:
                    continue

                complete_data = {**per_entity_pit, **global_data}
                try:
                    ctx_base = DataContext.assemble(
                        strategy_name=strategy_name,
                        settings=settings,
                        stock_list=[entity_id],
                        entity_id=entity_id,
                        entity_info={"id": entity_id, **self._stock_info.get(entity_id, {})},
                    )
                    ctx = DataContext.fill(
                        ctx_base,
                        now=now,
                        data=complete_data,
                        calendar=calendar_dict,
                    )
                except Exception as exc:
                    logger.error(
                        "构建 DataContext 失败：entity_id=%s now=%s error=%s",
                        entity_id,
                        now,
                        exc,
                        exc_info=True,
                    )
                    continue

                try:
                    scanned = hooks.scan_opportunity(ctx)
                except Exception as exc:
                    logger.error(
                        "scan_opportunity 失败：entity_id=%s now=%s error=%s",
                        entity_id,
                        now,
                        exc,
                        exc_info=True,
                    )
                    continue

                if not isinstance(scanned, Opportunity):
                    continue

                tracker.track_opportunity(
                    scanned,
                    settings=settings_dict,
                    strategy_name=strategy_name,
                    stock_info=self._stock_info.get(entity_id, {"id": entity_id}),
                    trigger_date=now,
                    trigger_price=float(bar["close"]),
                )

        last_day = filtered_dates[-1]
        for entity_id, tracker in self.trackers.items():
            if not tracker.active:
                continue
            last_bar = self._last_bar_by_entity.get(entity_id)
            if last_bar is None:
                continue
            tracker.settle_incomplete(last_day, last_bar)

        return self.trackers

    def total_recorded_count(self) -> int:
        return sum(len(tracker.recorded) for tracker in self.trackers.values())

    def entities_with_opportunities(self) -> int:
        return sum(1 for tracker in self.trackers.values() if tracker.recorded)

    def buffer_for_recorder(self) -> List[Dict[str, Any]]:
        """展平为 recorder buffer 条目。"""
        rows: List[Dict[str, Any]] = []
        for entity_id, tracker in self.trackers.items():
            for opp_dict in tracker.recorded_as_dicts():
                rows.append(
                    {
                        "entity_id": entity_id,
                        "date": opp_dict.get("trigger_date") or opp_dict.get("scan_date") or "",
                        "opportunity": opp_dict,
                    }
                )
        return rows

    @staticmethod
    def _load_pit_by_entity(
        entity_contracts: Dict[str, Any],
        as_of: str,
    ) -> Dict[str, Dict[str, Any]]:
        pit_data_by_entity: Dict[str, Dict[str, Any]] = {}
        for data_key, contract in entity_contracts.items():
            try:
                pit_data_dict = contract.until(as_of=as_of)
            except Exception as exc:
                logger.error(
                    "Contract.until 失败：data_key=%s as_of=%s error=%s",
                    data_key,
                    as_of,
                    exc,
                    exc_info=True,
                )
                continue
            for entity_id, pit_rows in pit_data_dict.items():
                pit_data_by_entity.setdefault(entity_id, {})[data_key] = pit_rows
        return pit_data_by_entity

    @staticmethod
    def _bar_on(
        per_entity_pit: Dict[str, Any],
        *,
        base_data_key: str,
        as_of: str,
        min_required: int,
    ) -> Optional[Dict[str, Any]]:
        base_rows = per_entity_pit.get(base_data_key)
        if not isinstance(base_rows, list) or not base_rows:
            return None
        last = base_rows[-1]
        if str(last.get("date") or "") != as_of:
            return None
        if len(base_rows) < min_required:
            return None
        for key in ("open", "high", "low", "close"):
            if key not in last:
                raise ValueError(f"K 线缺少字段 {key!r}: date={as_of}")
        return last

    @staticmethod
    def _resolve_max_holding_days(settings: Dict[str, Any]) -> int:
        simulation = settings.get("simulation")
        if not isinstance(simulation, dict):
            return 0
        max_days = simulation.get("max_holding_days")
        if max_days is None:
            return 0
        if not isinstance(max_days, int) or max_days < 0:
            raise ValueError("settings.simulation.max_holding_days 须为非负整数")
        return max_days


__all__ = ["EntityEnumerationSimulator"]
