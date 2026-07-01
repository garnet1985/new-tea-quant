#!/usr/bin/env python3
"""Scanner / simulate subprocess runner (framework-owned orchestration)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.market_profile import get_market_profile
from core.modules.strategy.enums import ExecutionMode
from core.modules.strategy.engines.shared.data_classes.investment_state import (
    InvestmentLifecycle,
    ScanSignalPhase,
)
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.market_profile_id import (
    resolve_market_profile_id,
)
from core.modules.strategy.engines.shared.helpers.simulation_day_execution import (
    execute_pending_exits_on_active,
    fill_pending_buys,
    queue_deferred_buy,
    resolve_pending_buys_at_end,
    resolve_pending_exits_on_active_at_end,
)
from core.modules.strategy.engines.shared.helpers.simulation_pricing import (
    apply_buy_slippage,
    trade_price_defers_to_next_session,
    trade_theoretical_price_same_day,
)
from core.modules.strategy.engines.shared.helpers.skip_investment_when import (
    stamp_stock_status_at_trigger,
)
from core.modules.strategy.engines.shared.helpers.stock_status_risk_context import (
    build_stock_status_risk_runtime_context,
)
from core.modules.strategy.engines.shared.helpers.tradability import annotate_scan_opportunity
from core.modules.strategy.hooks import (
    StrategyHookRuntime,
    entity_context,
    scan_context,
)
from core.modules.strategy.services.data import StrategyDataInjectionService

logger = logging.getLogger(__name__)

MAX_LOOKBACK_DAYS = 60


def _active_list_from_investing(tracker: Dict[str, Any]) -> List[Opportunity]:
    investing = tracker.get("investing")
    return [investing] if investing is not None else []


class StrategyScannerRunner:
    """执行 scan / simulate job payload；用户逻辑经 ``StrategyHookRuntime`` 调用。"""

    def __init__(self, job_payload: Dict[str, Any]) -> None:
        self.job_payload = job_payload
        self.stock_id = job_payload["stock_id"]
        self.execution_mode = job_payload["execution_mode"]
        self.strategy_name = job_payload["strategy_name"]
        self.settings = StrategySettingsView.from_dict(job_payload["settings"])
        self.simulation = self.settings.simulation_settings
        profile_id = resolve_market_profile_id(
            job_payload,
            settings_market_profile=self.settings.market_profile,
        )
        self.market_profile = get_market_profile(profile_id)
        self.contract_cache = ContractCacheManager()
        self.stock_info = self._load_stock_info()
        period_start = str(job_payload.get("start_date") or self.settings.start_date or "")
        period_end = str(job_payload.get("end_date") or self.settings.end_date or "")
        self.stock_status_risk = build_stock_status_risk_runtime_context(
            stock_meta=self.stock_info,
            settings=self.settings.stock_status_risk,
            stock_id=self.stock_id,
            period_start=period_start,
            period_end=period_end,
        )
        self.data_manager = StrategyDataInjectionService(
            stock_id=self.stock_id,
            settings=self.settings,
            contract_cache=self.contract_cache,
        )
        self.hook_runtime = StrategyHookRuntime.from_job_payload(
            job_payload,
            settings=self.settings,
        )
        if self.execution_mode == ExecutionMode.SIMULATE.value:
            raw_opportunity = job_payload.get("opportunity")
            self.opportunity = Opportunity.from_dict(raw_opportunity) if raw_opportunity else None
            self.end_date = job_payload["end_date"]
        else:
            self.scan_date = job_payload.get("scan_date")
        init_ctx = entity_context(
            strategy_name=self.strategy_name,
            settings=self.settings,
            stock_id=self.stock_id,
            job_payload=self.job_payload,
            stock_info=self.stock_info,
            data_manager=self.data_manager,
        )
        self.hook_runtime.call("on_entity_init", init_ctx)

    def _load_stock_info(self) -> Dict[str, Any]:
        from core.modules.strategy.services.execution.worker_runtime import (
            resolve_strategy_worker_data_manager,
        )

        try:
            stock_info = resolve_strategy_worker_data_manager().stock.list.load_single(
                self.stock_id,
            )
            if isinstance(stock_info, dict):
                return stock_info
            if str(self.stock_id).upper() != "DUMMY":
                logger.warning("无法加载股票信息: %s，使用最小信息", self.stock_id)
            return {
                "id": self.stock_id,
                "name": self.stock_id,
                "industry": "",
                "type": "",
                "exchange_center": "",
            }
        except Exception as exc:
            if str(self.stock_id).upper() != "DUMMY":
                logger.error("加载股票信息失败: %s, error: %s", self.stock_id, exc)
            return {
                "id": self.stock_id,
                "name": self.stock_id,
                "industry": "",
                "type": "",
                "exchange_center": "",
            }

    def run(self) -> Dict[str, Any]:
        try:
            if self.execution_mode == ExecutionMode.SCAN.value:
                return self._execute_scan()
            if self.execution_mode == ExecutionMode.SIMULATE.value:
                return self._execute_simulate()
            raise ValueError(f"未知的执行模式: {self.execution_mode}")
        except Exception as exc:
            logger.error(
                "处理股票失败: stock_id=%s, strategy=%s, mode=%s, error=%s",
                self.stock_id,
                self.strategy_name,
                self.execution_mode,
                exc,
                exc_info=True,
            )
            return {
                "success": False,
                "stock_id": self.stock_id,
                "opportunity": None,
                "error": str(exc),
            }

    def _scan_ctx(
        self,
        data: Dict[str, Any],
        *,
        opportunity: Optional[Opportunity] = None,
    ):
        return scan_context(
            strategy_name=self.strategy_name,
            settings=self.settings,
            stock_id=self.stock_id,
            job_payload=self.job_payload,
            stock_info=self.stock_info,
            data=data,
            scan_date=getattr(self, "scan_date", None),
            opportunity=opportunity,
            data_manager=self.data_manager,
        )

    def _execute_scan(self) -> Dict[str, Any]:
        lookback = min(self.settings.min_required_records, MAX_LOOKBACK_DAYS)
        self.data_manager.load_latest_data(lookback=lookback)
        data = self.data_manager.get_loaded_data()
        self.hook_runtime.call("on_before_scan", self._scan_ctx(data))
        opportunity = self.hook_runtime.call("scan_opportunity", self._scan_ctx(data))
        if opportunity and opportunity.stock:
            opportunity.stock = {**self.stock_info, **opportunity.stock}
        if opportunity:
            trigger_day = str(
                opportunity.trigger_date
                or getattr(self, "scan_date", None)
                or ""
            ).strip()
            stamp_stock_status_at_trigger(
                opportunity,
                trade_date=trigger_day,
                tier_periods=self.stock_status_risk.tier_periods,
            )
            profile_id = resolve_market_profile_id(
                self.job_payload,
                settings_market_profile=self.settings.market_profile,
            )
            annotate_scan_opportunity(
                opportunity,
                profile=get_market_profile(profile_id),
                klines=self.data_manager.get_klines(),
                scan_date=getattr(self, "scan_date", None),
                stock_status_risk=self.stock_status_risk,
            )
        self.hook_runtime.call(
            "on_after_scan",
            self._scan_ctx(data, opportunity=opportunity),
        )
        return {
            "success": True,
            "stock_id": self.stock_id,
            "opportunity": opportunity.to_dict() if opportunity else None,
        }

    def _execute_simulate(self) -> Dict[str, Any]:
        lookback_days = min(self.settings.min_required_records, MAX_LOOKBACK_DAYS)
        actual_start_date = self._get_date_before(self.job_payload.get("start_date"), lookback_days)
        self.data_manager.load_historical_data(start_date=actual_start_date, end_date=self.end_date)
        all_klines = self.data_manager.get_klines()

        if not all_klines:
            logger.warning("没有K线数据: stock=%s", self.stock_id)
            return {"success": True, "stock_id": self.stock_id, "settled": []}

        tracker: Dict[str, Any] = {
            "stock_id": self.stock_id,
            "passed_dates": [],
            "pending_buys": [],
            "investing": None,
            "settled": [],
        }
        min_required_kline = self.settings.min_required_records
        last_kline = None
        for idx, current_kline in enumerate(all_klines):
            virtual_date_of_today = current_kline["date"]
            tracker["passed_dates"].append(virtual_date_of_today)
            if len(tracker["passed_dates"]) < min_required_kline:
                continue
            data_of_today = self.data_manager.get_data_until(virtual_date_of_today)
            prev_kline = all_klines[idx - 1] if idx > 0 else None
            self._execute_single_day(
                tracker,
                current_kline,
                data_of_today,
                prev_kline=prev_kline,
            )
            last_kline = current_kline

        if last_kline:
            resolve_pending_buys_at_end(
                tracker["pending_buys"],
                _active_list_from_investing(tracker),
                [],
                sim=self.simulation,
            )
            if tracker["pending_buys"]:
                tracker["investing"] = tracker["pending_buys"][0]
                tracker["pending_buys"].clear()
            resolve_pending_exits_on_active_at_end(
                _active_list_from_investing(tracker),
                last_bar=last_kline,
                sim=self.simulation,
            )
            if tracker["investing"]:
                self._settle_open_opportunity(tracker, last_kline)

        del tracker["passed_dates"]
        del tracker["investing"]
        return {"success": True, "stock_id": self.stock_id, "settled": tracker["settled"]}

    def _execute_single_day(
        self,
        tracker: Dict[str, Any],
        current_kline: Dict[str, Any],
        data_of_today: Dict[str, Any],
        *,
        prev_kline: Optional[Dict[str, Any]] = None,
    ) -> None:
        active = _active_list_from_investing(tracker)
        fill_pending_buys(
            tracker["pending_buys"],
            active,
            bar=current_kline,
            sim=self.simulation,
        )
        if active and tracker["investing"] is None:
            tracker["investing"] = active[0]

        if tracker["investing"]:
            exit_indices = execute_pending_exits_on_active(
                active,
                bar=current_kline,
                sim=self.simulation,
            )
            if exit_indices:
                completed_opportunity = tracker["investing"]
                tracker["settled"].append(completed_opportunity.to_dict())
                tracker["investing"] = None
            else:
                is_completed = tracker["investing"].check_targets(
                    self.simulation,
                    current_kline=current_kline,
                    goal_config=self.settings.goal,
                    prev_bar=prev_kline,
                    market_profile=self.market_profile,
                    stock_status_risk=self.stock_status_risk,
                )
                if is_completed:
                    tracker["settled"].append(tracker["investing"].to_dict())
                    tracker["investing"] = None

        if tracker["investing"] is None and not tracker["pending_buys"]:
            opportunity = self.hook_runtime.call(
                "scan_opportunity",
                self._scan_ctx(data_of_today),
            )
            if opportunity:
                opportunity.trigger_date = current_kline["date"]
                opportunity.trigger_price = float(current_kline.get("close") or 0.0)
                if trade_price_defers_to_next_session(self.simulation.buy_price_model):
                    queue_deferred_buy(opportunity, signal_bar=current_kline)
                    tracker["pending_buys"].append(opportunity)
                    return
                buy_raw = trade_theoretical_price_same_day(
                    self.simulation.buy_price_model,
                    side="buy",
                    bar=current_kline,
                    no_next_bar=self.simulation.edges_no_next_bar,
                )
                if buy_raw is None:
                    return
                opportunity.buy_price = apply_buy_slippage(buy_raw, self.simulation.slippage_buy_bps)
                opportunity.buy_date = str(current_kline.get("date") or "")
                opportunity.signal_phase = ScanSignalPhase.ACTIVE.value
                opportunity.lifecycle = InvestmentLifecycle.OPEN.value
                tracker["investing"] = opportunity

    def _settle_open_opportunity(
        self,
        tracker: Dict[str, Any],
        last_kline: Dict[str, Any],
    ) -> None:
        opportunity = tracker.get("investing")
        if not opportunity:
            return
        opportunity.settle(
            self.simulation,
            last_kline=last_kline,
            reason="backtest_end",
        )
        tracker["settled"].append(opportunity.to_dict())
        tracker["investing"] = None

    def _get_date_before(self, date: str, days: int) -> str:
        from core.utils.date.date_utils import DateUtils

        try:
            adjusted_days = int(days * 1.5)
            return DateUtils.sub_days(date, adjusted_days)
        except Exception as exc:
            logger.error("计算日期失败: date=%s, days=%s, error=%s", date, days, exc)
            return date


def run_scanner_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return StrategyScannerRunner(payload).run()


__all__ = ["StrategyScannerRunner", "run_scanner_payload"]
