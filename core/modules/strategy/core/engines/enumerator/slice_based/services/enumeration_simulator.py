"""slice_based 枚举模拟：calendar asof → EntityTracker(Investment) → scan。"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.contracts import CalendarAsOfResult, Opportunity
from core.modules.strategy.core.engines.enumerator.shared.services.enum_job_perf import (
    EnumJobPerfRecorder,
)
from core.modules.strategy.core.engines.enumerator.shared.state.entity_tracker import (
    EntityTracker,
)
from core.modules.strategy.core.engines.shared.data_class import InvestmentTickInput
from core.modules.strategy.core.engines.shared.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.context.data_context import DataContext

logger = logging.getLogger(__name__)


@dataclass
class SliceEnumerationSimulator:
    """在 slice job 内驱动「open_dates × entities」枚举。

    边界:
    - 负责: asof 选股、Investment 生命周期、换仓 settle、head 片 wall/RSS 采样
    - 不负责: Contract 加载、CSV 落盘、BE reader/preload
    - 调用方: slice_based.JobExecutor

    状态：每 entity 一份 shared ``EntityTracker``。
    钩子：on_calendar_asof →（选出的 stocks）before/scan/after → register Investment。

    TODO(extract-shared): calendar 日循环骨架与 entity EntityEnumerationSimulator 接近；
    差异在 asof 选股与全量 universe 上下文。
    """

    entity_ids: List[str]
    trackers: Dict[str, EntityTracker] = field(init=False)
    _stock_info: Dict[str, Dict[str, Any]] = field(init=False, repr=False)
    _session_state: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _open_dates: List[str] = field(default_factory=list, init=False, repr=False)
    _last_bar_by_entity: Dict[str, Dict[str, Any]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        ids = [str(eid).strip() for eid in self.entity_ids if str(eid).strip()]
        self.entity_ids = ids
        self.trackers = {eid: EntityTracker(entity_id=eid) for eid in ids}
        self._stock_info = {eid: StockMetaHelper.load(eid) for eid in ids}

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
        payload: Dict[str, Any],
        perf: Optional[EnumJobPerfRecorder] = None,
    ) -> None:
        settings_dict = settings.to_dict()
        self._assert_entry_price_model(settings_dict)
        rebalance_period = self._resolve_rebalance_period(settings_dict)

        resolver = StrategyDataResolver(settings_dict)
        base_data_key = str(resolver.base.get("data_key") or "").strip()
        if not base_data_key:
            raise ValueError("settings.data.base.data_key 不能为空")
        min_required = resolver.min_required_records

        filtered_dates = [
            day for day in open_dates if str(start_date) <= str(day) <= str(end_date)
        ]
        if not filtered_dates:
            logger.warning("无有效 open_dates：%s ~ %s", start_date, end_date)
            return
        self._open_dates = list(filtered_dates)
        open_dates_tuple = tuple(filtered_dates)

        slice_open_days = max(
            1,
            int(
                payload.get("_slice_open_days")
                or (payload.get("_slice_plan") or {}).get("slice_open_days")
                or 20
            ),
        )
        head_sample_slices = max(0, int(payload.get("_slice_head_sample_slices") or 0))
        self._slice_samples: List[Dict[str, Any]] = []
        self._baseline_rss_mb = SliceEnumerationSimulator._process_rss_mb()

        ctx_base = DataContext.assemble(
            strategy_name=strategy_name,
            settings=settings,
            stock_list=list(self.entity_ids),
        )

        window_start_idx = 0
        slice_index = 0
        window_t0 = time.perf_counter()

        for index, as_of in enumerate(filtered_dates):
            if perf is not None:
                perf.begin("enum_pit_until")
            pit_by_entity = self._load_pit_by_entity(entity_contracts, as_of, perf=perf)
            if perf is not None:
                perf.end("enum_pit_until", accumulate=True)

            # 1) Investment.tick（止盈止损 / 到期等，由 Investment execute_steps 管）
            for entity_id, tracker in self.trackers.items():
                bar = self._bar_on(
                    pit_by_entity.get(entity_id, {}),
                    base_data_key=base_data_key,
                    as_of=as_of,
                    min_required=min_required,
                )
                if bar is None:
                    continue
                self._last_bar_by_entity[entity_id] = bar
                if perf is not None:
                    perf.begin("enum_process_tick")
                tracker.process_tick(
                    InvestmentTickInput(as_of_date=as_of, bar=bar, data_as_of=as_of)
                )
                if perf is not None:
                    perf.end("enum_process_tick", accumulate=True)

            stocks_ctx = self._build_stocks_context(
                pit_by_entity,
                base_data_key=base_data_key,
                as_of=as_of,
                min_required=min_required,
                global_data=global_data,
            )
            calendar = self._build_calendar_view(
                as_of,
                stocks=stocks_ctx,
                open_date_index=index,
                rebalance_period=rebalance_period,
            )

            # 2) on_calendar_asof
            asof_ctx = DataContext.fill(ctx_base, now=as_of, calendar=calendar)
            try:
                if perf is not None:
                    perf.begin("enum_calendar_asof")
                asof_result = hooks.on_calendar_asof(asof_ctx)
                if perf is not None:
                    perf.end("enum_calendar_asof", accumulate=True)
            except Exception as exc:
                if perf is not None:
                    perf.end("enum_calendar_asof", accumulate=True)
                logger.error(
                    "on_calendar_asof 失败：as_of=%s error=%s",
                    as_of,
                    exc,
                    exc_info=True,
                )
                continue

            if not isinstance(asof_result, CalendarAsOfResult):
                raise TypeError(
                    f"on_calendar_asof 必须返回 CalendarAsOfResult，实际: {type(asof_result).__name__}"
                )
            self._session_state = dict(asof_result.session_state)
            calendar["session_state"] = dict(self._session_state)

            # 3) 换仓清仓日：settle 所有未完结 Investment
            force_exit_date = str(self._session_state.get("force_exit_open_date") or "").strip()
            if force_exit_date == as_of:
                for entity_id, tracker in self.trackers.items():
                    if not tracker.active:
                        continue
                    bar = self._last_bar_by_entity.get(entity_id)
                    if bar is None:
                        continue
                    tracker.settle_incomplete(
                        InvestmentTickInput(as_of_date=as_of, bar=bar, data_as_of=as_of)
                    )

            # 4) 选出的 stocks → scan → register Investment
            for stock_id in asof_result.stocks:
                entity_id = str(stock_id).strip()
                tracker = self.trackers.get(entity_id)
                if tracker is None:
                    raise ValueError(f"on_calendar_asof 返回未知 stock_id: {entity_id}")
                self._scan_entity(
                    tracker=tracker,
                    entity_id=entity_id,
                    as_of=as_of,
                    pit_by_entity=pit_by_entity,
                    global_data=global_data,
                    base_data_key=base_data_key,
                    min_required=min_required,
                    calendar=calendar,
                    settings=settings,
                    hooks=hooks,
                    strategy_name=strategy_name,
                    ctx_base=ctx_base,
                    open_dates=open_dates_tuple,
                    perf=perf,
                )

            # Logical slice boundary sample (head windows only).
            days_in_window = index - window_start_idx + 1
            hit_window_end = days_in_window >= slice_open_days
            is_last_day = index == len(filtered_dates) - 1
            if (
                head_sample_slices > 0
                and slice_index < head_sample_slices
                and (hit_window_end or is_last_day)
            ):
                elapsed = max(0.0, time.perf_counter() - window_t0)
                rss = SliceEnumerationSimulator._process_rss_mb()
                # Day-loop fuses PIT+scan; split wall evenly so preload ratio is defined.
                half = round(elapsed / 2.0, 4)
                self._slice_samples.append(
                    {
                        "slice_index": slice_index,
                        "load_sec": half,
                        "compute_sec": half,
                        "serialize_sec": 0.0,
                        "deserialize_sec": 0.0,
                        "rss_after_mb": round(rss, 1),
                        "payload_mb": round(
                            max(0.0, rss - self._baseline_rss_mb), 1
                        ),
                        "payload_bytes": int(
                            max(0.0, rss - self._baseline_rss_mb) * 1024 * 1024
                        ),
                    }
                )
                slice_index += 1
                window_start_idx = index + 1
                window_t0 = time.perf_counter()

        # 5) 区间结束仍未平仓 → settle
        last_day = filtered_dates[-1]
        for entity_id, tracker in self.trackers.items():
            if not tracker.active:
                continue
            last_bar = self._last_bar_by_entity.get(entity_id)
            if last_bar is None:
                continue
            tracker.settle_incomplete(
                InvestmentTickInput(as_of_date=last_day, bar=last_bar, data_as_of=last_day)
            )

    def _scan_entity(
        self,
        *,
        tracker: EntityTracker,
        entity_id: str,
        as_of: str,
        pit_by_entity: Dict[str, Dict[str, Any]],
        global_data: Dict[str, Any],
        base_data_key: str,
        min_required: int,
        calendar: Dict[str, Any],
        settings: StrategySettings,
        hooks: Any,
        strategy_name: str,
        ctx_base: DataContext,
        open_dates: Sequence[str],
        perf: Optional[EnumJobPerfRecorder],
    ) -> None:
        # 已有未完结仓位时跳过（换仓日应先 settle）
        if tracker.active:
            logger.debug(
                "skip scan：entity=%s as_of=%s 仍有 active investments=%d",
                entity_id,
                as_of,
                len(tracker.active),
            )
            return

        per_entity_pit = pit_by_entity.get(entity_id, {})
        bar = self._bar_on(
            per_entity_pit,
            base_data_key=base_data_key,
            as_of=as_of,
            min_required=min_required,
        )
        if bar is None:
            return

        complete_data = dict(per_entity_pit)
        if global_data:
            complete_data = {**global_data, **per_entity_pit}

        stock_info = self._stock_info.get(entity_id, {"id": entity_id})
        scan_ctx = DataContext.fill(
            ctx_base,
            now=as_of,
            data=complete_data,
            calendar=calendar,
            entity_id=entity_id,
            entity_info={"id": entity_id, **stock_info},
        )

        try:
            if perf is not None:
                perf.begin("enum_scan")
            hooks.on_before_scan(scan_ctx)
            opportunity = hooks.scan_opportunity(scan_ctx)
            hooks.on_after_scan(
                DataContext.fill(
                    ctx_base,
                    now=as_of,
                    data=complete_data,
                    calendar=calendar,
                    entity_id=entity_id,
                    entity_info={"id": entity_id, **stock_info},
                    opportunity=opportunity if isinstance(opportunity, Opportunity) else None,
                )
            )
            if perf is not None:
                perf.end("enum_scan", accumulate=True)
        except Exception as exc:
            if perf is not None:
                perf.end("enum_scan", accumulate=True)
            logger.error(
                "scan 失败：entity_id=%s as_of=%s error=%s",
                entity_id,
                as_of,
                exc,
                exc_info=True,
            )
            return

        if not isinstance(opportunity, Opportunity):
            return

        tracker.register_from_opportunity(
            opportunity,
            settings=settings,
            open_dates=open_dates,
            strategy_name=strategy_name,
            stock_info=stock_info,
            trigger_date=as_of,
            trigger_price=float(bar["close"]),
        )
        # buy_price_model=close|open 只能在 trigger 日成交；须在 register 后补 tick
        tracker.process_tick(
            InvestmentTickInput(as_of_date=as_of, bar=bar, data_as_of=as_of)
        )

    def total_recorded_count(self) -> int:
        return sum(len(tracker.recorded) for tracker in self.trackers.values())

    def entities_with_investments(self) -> int:
        return sum(1 for tracker in self.trackers.values() if tracker.recorded)

    def buffer_for_recorder(self) -> List[Dict[str, Any]]:
        # TODO(extract-shared): 与 entity EntityEnumerationSimulator.buffer_for_recorder 同形
        rows: List[Dict[str, Any]] = []
        for entity_id, tracker in self.trackers.items():
            for inv_dict in tracker.recorded_as_dicts():
                rows.append(
                    {
                        "entity_id": entity_id,
                        "date": inv_dict.get("trigger_date") or "",
                        "opportunity": inv_dict,
                    }
                )
        return rows

    def slice_runtime_plan_dict(self) -> Dict[str, Any]:
        samples = list(getattr(self, "_slice_samples", None) or [])
        return {
            "baseline_rss_mb": float(getattr(self, "_baseline_rss_mb", 0.0) or 0.0),
            "slice_samples": samples,
        }

    @staticmethod
    def _process_rss_mb() -> float:
        try:
            import os

            import psutil

            return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
        except Exception:
            return 0.0

    def _build_stocks_context(
        self,
        pit_by_entity: Dict[str, Dict[str, Any]],
        *,
        base_data_key: str,
        as_of: str,
        min_required: int,
        global_data: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for entity_id in self.entity_ids:
            per_entity = pit_by_entity.get(entity_id, {})
            if (
                self._bar_on(
                    per_entity,
                    base_data_key=base_data_key,
                    as_of=as_of,
                    min_required=min_required,
                )
                is None
            ):
                continue
            if global_data:
                packed = {**global_data, **per_entity}
            else:
                packed = dict(per_entity)
            base_rows = packed.get(base_data_key)
            if isinstance(base_rows, list) and "klines" not in packed:
                packed["klines"] = base_rows
            out[entity_id] = packed
        return out

    def _build_calendar_view(
        self,
        as_of: str,
        *,
        stocks: Dict[str, Dict[str, Any]],
        open_date_index: int,
        rebalance_period: str,
    ) -> Dict[str, Any]:
        all_open: Sequence[str] = self._open_dates
        if rebalance_period == "month":
            is_period_start = CalendarOpenDateHelper.is_first_open_of_month(as_of, all_open)
            is_period_end = CalendarOpenDateHelper.is_last_open_of_month(as_of, all_open)
        else:
            is_period_start = CalendarOpenDateHelper.is_first_open_of_year(as_of, all_open)
            is_period_end = CalendarOpenDateHelper.is_last_open_of_year(as_of, all_open)
        return {
            "as_of_date": as_of,
            "session_state": dict(self._session_state),
            "stocks": dict(stocks),
            "open_date_index": open_date_index,
            "is_period_start": is_period_start,
            "is_period_end": is_period_end,
            "is_first_open_of_month": CalendarOpenDateHelper.is_first_open_of_month(as_of, all_open),
            "is_last_open_of_month": CalendarOpenDateHelper.is_last_open_of_month(as_of, all_open),
            "is_first_open_of_year": CalendarOpenDateHelper.is_first_open_of_year(as_of, all_open),
            "is_last_open_of_year": CalendarOpenDateHelper.is_last_open_of_year(as_of, all_open),
        }

    @staticmethod
    def _resolve_rebalance_period(settings: Dict[str, Any]) -> str:
        core = settings.get("core")
        if not isinstance(core, dict):
            return "year"
        period = str(core.get("rebalance_period") or "year").strip().lower()
        return period if period in {"month", "year"} else "year"

    @staticmethod
    def _assert_entry_price_model(settings: Dict[str, Any]) -> None:
        simulation = settings.get("simulation")
        if not isinstance(simulation, dict):
            return
        model = simulation.get("buy_price_model")
        if model is None:
            return
        if model != "close":
            raise ValueError(
                f"slice_based 当前仅支持 simulation.buy_price_model='close'，实际: {model!r}"
            )

    @staticmethod
    def _load_pit_by_entity(
        entity_contracts: Dict[str, Any],
        as_of: str,
        *,
        perf: Optional[EnumJobPerfRecorder] = None,
    ) -> Dict[str, Dict[str, Any]]:
        # TODO(extract-shared): 与 entity_based._load_pit_by_entity 相同
        pit_data_by_entity: Dict[str, Dict[str, Any]] = {}
        for data_key, contract in entity_contracts.items():
            try:
                until_t0 = time.perf_counter()
                pit_data_dict = contract.until(as_of=as_of)
                if perf is not None:
                    perf.record_contract_until(
                        str(data_key),
                        time.perf_counter() - until_t0,
                    )
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
        # TODO(extract-shared): 与 entity_based._bar_on 相同
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


__all__ = ["SliceEnumerationSimulator"]
