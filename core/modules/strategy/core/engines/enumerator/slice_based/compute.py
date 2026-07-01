"""slice_based 核心计算：on_calendar_asof → holdings → scan。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Sequence

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.enumerator.slice_based.context.data import SliceDataContext
from core.modules.strategy.core.engines.enumerator.slice_based.resolver.calendar import BacktestCalendarResolver
from core.modules.strategy.core.engines.enumerator.slice_based.state.holdings import EntityHoldings
from core.modules.strategy.core.engines.shared.data_classes import Opportunity
from core.modules.strategy.core.engines.shared.data_classes.calendar_as_of import CalendarAsOfResult
from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper
from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
from core.modules.strategy.core.helpers.opportunity_enrichment import OpportunityEnricher
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.data.entity_data import EntityContractBatch, EntityDataLoader
from core.modules.strategy.core.services.data.strategy_data_config import StrategyDataConfig

logger = logging.getLogger(__name__)


@dataclass
class _EntitySliceState:
    stock_id: str
    stock_info: Dict[str, Any]
    data_loader: EntityDataLoader
    holdings: EntityHoldings
    opp_counter: int = 0


class SliceBasedCompute:
    """单进程 slice 计算：按 open_dates 驱动 asof + holdings + scan。"""

    def __init__(self, job_payload: Dict[str, Any]) -> None:
        self.job_payload = dict(job_payload)
        stock_ids_raw = self.job_payload.get("stock_ids")
        if not isinstance(stock_ids_raw, list) or not stock_ids_raw:
            raise ValueError("SliceBasedCompute 缺少非空 stock_ids")
        self.stock_ids = [str(s).strip() for s in stock_ids_raw if str(s).strip()]
        if not self.stock_ids:
            raise ValueError("SliceBasedCompute stock_ids 无有效条目")

        self.strategy_name = str(self.job_payload["strategy_name"])
        self.start_date = str(self.job_payload["start_date"])
        self.end_date = str(self.job_payload["end_date"])
        self.output_dir = str(self.job_payload["output_dir"])

        settings_raw = self.job_payload.get("settings")
        if not isinstance(settings_raw, dict):
            raise ValueError("SliceBasedCompute 缺少 settings")
        self.settings = StrategySettings(raw_settings=settings_raw)
        self.settings.apply_defaults()
        self._data_config = StrategyDataConfig(settings_raw)
        self._min_required = self._data_config.min_required_records
        self._max_holding_days = self._resolve_max_holding_days(settings_raw)

        self._open_dates = self._resolve_open_dates()
        self._hook_runtime = StrategyHookRuntime.from_job_payload(
            self.job_payload,
            settings=self.settings,
        )
        self._session_state: Dict[str, Any] = {}
        self._states: Dict[str, _EntitySliceState] = {}
        self._stock_list: List[str] = []

    def run(self) -> Dict[str, Any]:
        try:
            self._hydrate_entity_data()
            for index, as_of in enumerate(self._open_dates):
                self._run_open_date(as_of, open_date_index=index)

            stock_results = [self._state_result(state) for state in self._states.values()]
            self._write_outputs(stock_results)

            return {
                "success": all(bool(row.get("success")) for row in stock_results),
                "bulk": True,
                "stock_results": stock_results,
                "stock_ids": list(self.stock_ids),
                "session_state": dict(self._session_state),
                "open_dates_processed": len(self._open_dates),
            }
        finally:
            self._clear_loaders()

    def _resolve_max_holding_days(self, settings: Dict[str, Any]) -> int:
        simulation = settings.get("simulation")
        if not isinstance(simulation, dict):
            return 0
        max_days = simulation.get("max_holding_days")
        if max_days is None:
            return 0
        if not isinstance(max_days, int) or max_days < 0:
            raise ValueError("settings.simulation.max_holding_days 须为非负整数")
        return max_days

    def _resolve_open_dates(self) -> List[str]:
        calendar = self.job_payload.get("backtest_calendar")
        if not isinstance(calendar, dict):
            raise ValueError("SliceBasedCompute 缺少 backtest_calendar")
        raw = calendar.get("open_dates")
        if not isinstance(raw, list) or not raw:
            raise ValueError("backtest_calendar.open_dates 须为非空 list")
        open_dates = BacktestCalendarResolver.filter_in_range(raw, self.start_date, self.end_date)
        if not open_dates:
            raise ValueError(
                f"slice_based 无有效 open_dates: {self.start_date}—{self.end_date}"
            )
        return open_dates

    def _hydrate_entity_data(self) -> None:
        settings_dict = self.settings.to_dict()
        actual_start = EntityDataLoader.enumeration_actual_start_date(
            self.start_date,
            self._min_required,
        )
        global_data = self.job_payload.get("global_data")
        if not isinstance(global_data, dict):
            raise ValueError("SliceBasedCompute 缺少 global_data")

        shared_cache = ContractCacheManager()
        job_batch = EntityContractBatch.hydrate(
            entity_ids=self.stock_ids,
            settings=settings_dict,
            start=actual_start,
            end=self.end_date,
            contract_cache=shared_cache,
            global_data=global_data,
            fresh_strategy_cache=True,
        )

        stock_list = global_data.get("stock_list")
        if isinstance(stock_list, list) and stock_list:
            universe = [str(x).strip() for x in stock_list if str(x).strip()]
        else:
            universe = list(self.stock_ids)

        for stock_id in self.stock_ids:
            loader = EntityDataLoader(
                stock_id=stock_id,
                settings=settings_dict,
                global_data=global_data,
                contract_cache=shared_cache,
            )
            loader.load(
                actual_start,
                self.end_date,
                job_batch=job_batch,
                fresh_strategy_cache=False,
            )
            self._states[stock_id] = _EntitySliceState(
                stock_id=stock_id,
                stock_info=StockMetaHelper.load(stock_id),
                data_loader=loader,
                holdings=EntityHoldings(),
            )
        self._stock_list = universe

    def _run_open_date(self, as_of: str, *, open_date_index: int) -> None:
        for state in self._states.values():
            bar = self._bar_on(state, as_of)
            if bar is None:
                continue
            close_price = float(bar["close"])
            if self._max_holding_days > 0:
                state.holdings.close_expired(
                    as_of,
                    close_price,
                    max_holding_days=self._max_holding_days,
                    open_dates=self._open_dates,
                )

        stocks_ctx = self._build_stocks_context(as_of)
        calendar = self._build_calendar_view(
            as_of,
            stocks=stocks_ctx,
            open_date_index=open_date_index,
        )

        asof_ctx = SliceDataContext.assemble_asof(
            strategy_name=self.strategy_name,
            settings=self.settings,
            stock_list=list(self._stock_list),
            as_of=as_of,
            calendar=calendar,
        )
        asof_result = self._hook_runtime.call("on_calendar_asof", asof_ctx)
        if not isinstance(asof_result, CalendarAsOfResult):
            raise TypeError("on_calendar_asof 必须返回 CalendarAsOfResult")
        self._session_state = dict(asof_result.session_state)

        force_exit_date = str(self._session_state.get("force_exit_open_date") or "").strip()
        if force_exit_date == as_of:
            for state in self._states.values():
                bar = self._bar_on(state, as_of)
                if bar is None:
                    continue
                state.holdings.force_exit_all(
                    as_of,
                    float(bar["close"]),
                    reason="period_end",
                )

        for stock_id in asof_result.stocks:
            sid = str(stock_id).strip()
            if sid not in self._states:
                raise ValueError(f"on_calendar_asof 返回未知 stock_id: {sid}")
            self._scan_entity(self._states[sid], as_of, calendar=calendar)

    def _bar_on(self, state: _EntitySliceState, as_of: str) -> Optional[Dict[str, Any]]:
        data = state.data_loader.data_until(as_of)
        klines = data.get("klines")
        if not isinstance(klines, list) or not klines:
            return None
        last = klines[-1]
        if str(last.get("date") or "") != as_of:
            return None
        if len(klines) < self._min_required:
            return None
        return last

    def _build_stocks_context(self, as_of: str) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for sid, state in self._states.items():
            data = state.data_loader.data_until(as_of)
            klines = data.get("klines")
            if not isinstance(klines, list) or not klines:
                continue
            if str(klines[-1].get("date") or "") != as_of:
                continue
            if len(klines) < self._min_required:
                continue
            out[sid] = data
        return out

    def _build_calendar_view(
        self,
        as_of: str,
        *,
        stocks: Dict[str, Dict[str, Any]],
        open_date_index: int,
    ) -> Dict[str, Any]:
        all_open: Sequence[str] = self._open_dates
        return {
            "as_of_date": as_of,
            "session_state": dict(self._session_state),
            "stocks": dict(stocks),
            "open_date_index": open_date_index,
            "is_period_start": CalendarOpenDateHelper.is_first_open_of_year(as_of, all_open),
            "is_period_end": CalendarOpenDateHelper.is_last_open_of_year(as_of, all_open),
            "is_first_open_of_month": CalendarOpenDateHelper.is_first_open_of_month(as_of, all_open),
            "is_last_open_of_month": CalendarOpenDateHelper.is_last_open_of_month(as_of, all_open),
            "is_first_open_of_year": CalendarOpenDateHelper.is_first_open_of_year(as_of, all_open),
            "is_last_open_of_year": CalendarOpenDateHelper.is_last_open_of_year(as_of, all_open),
        }

    def _scan_entity(
        self,
        state: _EntitySliceState,
        as_of: str,
        *,
        calendar: Dict[str, Any],
    ) -> None:
        bar = self._bar_on(state, as_of)
        if bar is None:
            return
        data = state.data_loader.data_until(as_of)

        ctx = SliceDataContext.assemble_scan(
            strategy_name=self.strategy_name,
            settings=self.settings,
            stock_list=list(self._stock_list),
            entity_id=state.stock_id,
            entity_info=state.stock_info,
            as_of=as_of,
            data=data,
            calendar=calendar,
        )
        self._hook_runtime.call("on_before_scan", ctx)
        opportunity = self._hook_runtime.call("scan_opportunity", ctx)
        self._hook_runtime.call(
            "on_after_scan",
            SliceDataContext.assemble_scan(
                strategy_name=self.strategy_name,
                settings=self.settings,
                stock_list=list(self._stock_list),
                entity_id=state.stock_id,
                entity_info=state.stock_info,
                as_of=as_of,
                data=data,
                calendar=calendar,
                opportunity=opportunity if isinstance(opportunity, Opportunity) else None,
            ),
        )
        if not isinstance(opportunity, Opportunity):
            return

        state.opp_counter += 1
        OpportunityEnricher.apply_trigger_fields(
            opportunity,
            settings=self.settings.to_dict(),
            strategy_name=self.strategy_name,
            stock_id=state.stock_id,
            stock_info=state.stock_info,
            trigger_date=as_of,
            trigger_price=float(bar["close"]),
            opportunity_index=state.opp_counter,
        )
        state.holdings.register_entry(opportunity)

    def _state_result(self, state: _EntitySliceState) -> Dict[str, Any]:
        opportunities_dict = [row.to_dict() for row in state.holdings.recorded]
        return {
            "success": True,
            "stock_id": state.stock_id,
            "stock_name": str(state.stock_info.get("name") or state.stock_id),
            "opportunities": opportunities_dict,
            "opportunity_count": len(opportunities_dict),
        }

    def _write_outputs(self, stock_results: List[Dict[str, Any]]) -> None:
        if not self.output_dir:
            return
        output_dir = Path(self.output_dir)
        for row in stock_results:
            stock_id = str(row["stock_id"]).strip()
            opportunities = row["opportunities"]
            OpportunityCsvHelper.write(output_dir, stock_id, opportunities)

    def _clear_loaders(self) -> None:
        for state in self._states.values():
            state.data_loader.clear_working_state()


__all__ = ["SliceBasedCompute"]
