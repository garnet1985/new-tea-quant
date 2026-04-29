#!/usr/bin/env python3
"""
Base Strategy Worker - 策略 Worker 基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.strategy.enums import ExecutionMode, OpportunityStatus
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettings,
)

logger = logging.getLogger(__name__)

MAX_LOOKBACK_DAYS = 60


class BaseStrategyWorker(ABC):
    """策略 Worker 基类（子进程）"""

    def __init__(self, job_payload: Dict[str, Any]):
        self.job_payload = job_payload
        self.stock_id = job_payload["stock_id"]
        self.execution_mode = job_payload["execution_mode"]
        self.strategy_name = job_payload["strategy_name"]
        self.settings = StrategySettings.from_dict(job_payload["settings"])

        self.contract_cache = ContractCacheManager()
        self.stock_info = self._load_stock_info()
        from core.modules.strategy.services.data import StrategyDataManager

        self.data_manager = StrategyDataManager(
            stock_id=self.stock_id,
            settings=self.settings,
            contract_cache=self.contract_cache,
        )

        if self.execution_mode == ExecutionMode.SIMULATE.value:
            raw_opportunity = job_payload.get("opportunity")
            self.opportunity = Opportunity.from_dict(raw_opportunity) if raw_opportunity else None
            self.end_date = job_payload["end_date"]
        else:
            self.scan_date = job_payload.get("scan_date")

        self.on_init()

    def _load_stock_info(self) -> Dict[str, Any]:
        try:
            dcm = DataContractManager(contract_cache=self.contract_cache)
            stock_list_contract = dcm.issue(DataKey.STOCK_LIST, filtered=False)
            stock_list = list(stock_list_contract.data or [])
            stock_info = next((x for x in stock_list if x.get("id") == self.stock_id), None)
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

    def _execute_scan(self) -> Dict[str, Any]:
        lookback = min(self.settings.min_required_records, MAX_LOOKBACK_DAYS)
        self.data_manager.load_latest_data(lookback=lookback)
        data = self.data_manager.get_loaded_data()
        self.on_before_scan()
        opportunity = self.scan_opportunity(data, self.settings.to_dict())
        if opportunity and opportunity.stock:
            opportunity.stock = {**self.stock_info, **opportunity.stock}
        self.on_after_scan(opportunity)
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

        tracker = {"stock_id": self.stock_id, "passed_dates": [], "investing": None, "settled": []}
        min_required_kline = self.settings.min_required_records
        last_kline = None
        for current_kline in all_klines:
            virtual_date_of_today = current_kline["date"]
            tracker["passed_dates"].append(virtual_date_of_today)
            if len(tracker["passed_dates"]) < min_required_kline:
                continue
            data_of_today = self.data_manager.get_data_until(virtual_date_of_today)
            self._execute_single_day(tracker, current_kline, data_of_today)
            last_kline = current_kline

        if tracker["investing"] and last_kline:
            self._settle_open_opportunity(tracker, last_kline)

        del tracker["passed_dates"]
        del tracker["investing"]
        return {"success": True, "stock_id": self.stock_id, "settled": tracker["settled"]}

    def _execute_single_day(
        self,
        tracker: Dict[str, Any],
        current_kline: Dict[str, Any],
        data_of_today: Dict[str, Any],
    ) -> None:
        if tracker["investing"]:
            is_completed = tracker["investing"].check_targets(
                current_kline=current_kline,
                goal_config=self.settings.goal,
            )
            if is_completed:
                completed_opportunity = tracker["investing"]
                tracker["settled"].append(tracker["investing"].to_dict())
                tracker["investing"] = None
                logger.debug(
                    "投资完成: stock=%s, date=%s, reason=%s",
                    self.stock_id,
                    current_kline["date"],
                    completed_opportunity.sell_reason,
                )

        if tracker["investing"] is None:
            opportunity = self.scan_opportunity_with_data(data_of_today)
            if opportunity:
                opportunity.trigger_date = current_kline["date"]
                opportunity.trigger_price = current_kline["close"]
                opportunity.status = OpportunityStatus.ACTIVE.value
                tracker["investing"] = opportunity
                logger.debug(
                    "发现机会: stock=%s, date=%s, price=%s",
                    self.stock_id,
                    current_kline["date"],
                    current_kline["close"],
                )

    def _settle_open_opportunity(self, tracker: Dict[str, Any], last_kline: Dict[str, Any]) -> None:
        opportunity = tracker.get("investing")
        if not opportunity:
            return
        opportunity.settle(last_kline=last_kline, reason="backtest_end")
        tracker["settled"].append(opportunity.to_dict())
        tracker["investing"] = None
        logger.debug(
            "清算未结投资: stock=%s, date=%s, roi=%.2f%%",
            self.stock_id,
            last_kline["date"],
            opportunity.roi * 100,
        )

    def _get_date_before(self, date: str, days: int) -> str:
        from core.utils.date.date_utils import DateUtils

        try:
            adjusted_days = int(days * 1.5)
            return DateUtils.sub_days(date, adjusted_days)
        except Exception as exc:
            logger.error("计算日期失败: date=%s, days=%s, error=%s", date, days, exc)
            return date

    def scan_opportunity_with_data(self, data: Dict[str, Any]) -> Optional["Opportunity"]:
        return self.scan_opportunity(data, self.settings.to_dict())

    @abstractmethod
    def scan_opportunity(
        self,
        data: Dict[str, Any],
        settings: Dict[str, Any],
    ) -> Optional["Opportunity"]:
        pass

    def on_init(self) -> None:
        pass

    def on_before_scan(self) -> None:
        pass

    def on_after_scan(self, opportunity: Optional["Opportunity"]) -> None:
        pass

    def on_before_simulate(self, opportunity: "Opportunity") -> None:
        pass

    def on_after_simulate(self, opportunity: "Opportunity") -> None:
        pass

    def on_price_factor_before_process_stock(
        self,
        stock_id: str,
        opportunities: "list[dict]",
        config: "dict",
    ) -> None:
        return None

    def on_price_factor_after_process_stock(
        self,
        stock_id: str,
        stock_summary: "dict",
        config: "dict",
    ) -> "dict":
        return stock_summary

    def on_price_factor_opportunity_trigger(
        self,
        opportunity_row: "dict",
        config: "dict",
    ) -> "dict":
        return opportunity_row

    def on_price_factor_target_hit(
        self,
        target_row: "dict",
        opportunity_row: "dict",
        config: "dict",
    ) -> "dict":
        return target_row

    def on_capital_allocation_before_trigger_event(
        self,
        event: "Any",
        account: "Any",
        config: "Any",
    ):
        return event

    def on_capital_allocation_after_trigger_event(
        self,
        event: "Any",
        trade: "dict",
        account: "Any",
        config: "Any",
    ):
        return trade

    def on_capital_allocation_before_target_event(
        self,
        event: "Any",
        account: "Any",
        config: "Any",
    ):
        return event

    def on_capital_allocation_after_target_event(
        self,
        event: "Any",
        trade: "dict",
        account: "Any",
        config: "Any",
    ):
        return trade

    def on_capital_allocation_calculate_shares_to_buy(
        self,
        event: "Any",
        account: "Any",
        config: "Any",
        default_shares: int,
    ):
        return None

    def on_capital_allocation_calculate_shares_to_sell(
        self,
        event: "Any",
        position: "Any",
        config: "Any",
        default_shares: int,
    ):
        return None
