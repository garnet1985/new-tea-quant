#!/usr/bin/env python3
"""Input-side data injection service."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.data_cursor import DataCursorManager
from core.modules.indicator import IndicatorService
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.services.data.helper import (
    normalize_declaration_item,
    storage_key_for,
)
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)

class StrategyDataInjectionService:
    """Service for preparing and injecting strategy input data."""

    def __init__(
        self,
        stock_id: str,
        settings: StrategySettingsView,
        *,
        contract_cache: ContractCacheManager,
        global_extra_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        self.stock_id = stock_id
        self.settings = settings
        self._global_extra_cache = global_extra_cache
        self._contract_cache = contract_cache
        self._dcf_mgr: Optional[DataContractManager] = None

        self._current_data: Dict[str, List[Dict[str, Any]]] = {"klines": []}
        self._slot_contracts: Dict[str, DataContract] = {}
        self._cursor_mgr = DataCursorManager()
        self._cursor_name = f"strategy:{self.stock_id}"

    def _contract_manager(self) -> DataContractManager:
        if self._dcf_mgr is None:
            self._dcf_mgr = DataContractManager(contract_cache=self._contract_cache)
        return self._dcf_mgr

    @staticmethod
    def storage_key_for(data_id: DataKey) -> str:
        return storage_key_for(data_id)

    def issue_contracts(
        self,
        *,
        start: str,
        end: str,
        entity_id: Optional[str] = None,
        data_block: Optional[Dict[str, Any]] = None,
    ) -> Dict[DataKey, DataContract]:
        block = data_block if data_block is not None else self.settings.data
        st = StrategySettingsView({"data": block})
        declarations = st.required_data_sources
        eff_entity = entity_id.strip() if entity_id and str(entity_id).strip() else None

        out: Dict[DataKey, DataContract] = {}
        dcm = self._contract_manager()
        for raw in declarations:
            item = self._normalize_declaration_item(st, raw)
            dk = DataKey(str(item["data_id"]))
            params = dict(item.get("params") or {})
            spec = dcm.map.get(dk)
            if spec is None:
                raise ValueError(f"未注册的 data_id：{dk.value}")

            scope = spec.get("scope")
            if scope == ContractScope.PER_ENTITY and eff_entity is None:
                continue

            ent = eff_entity if scope == ContractScope.PER_ENTITY else None
            contract = dcm.issue(
                dk,
                entity_id=ent,
                start=start,
                end=end,
                **params,
            )
            if dk in out:
                raise ValueError(
                    f"data 声明中重复的 data_id：{dk.value!r}（dict 存储下无法同时保留两条）"
                )
            out[dk] = contract

        return out

    @staticmethod
    def _normalize_declaration_item(
        settings: StrategySettingsView,
        raw: Dict[str, Any],
    ) -> Dict[str, Any]:
        return normalize_declaration_item(settings, raw)

    def hydrate_row_slots(self, start_date: str, end_date: str) -> None:
        self._contract_cache.enter_strategy_run()
        self._slot_contracts = {}
        contracts = self.issue_contracts(
            start=start_date,
            end=end_date,
            entity_id=self.stock_id,
        )
        dcm = self._contract_manager()
        for dk, contract in contracts.items():
            spec = dcm.map.get(dk)
            slot = self.storage_key_for(dk)
            if (
                spec
                and spec.get("scope") == ContractScope.GLOBAL
                and self._global_extra_cache is not None
                and slot in self._global_extra_cache
            ):
                cached_rows = list(self._global_extra_cache[slot])
                contract.data = cached_rows
                self._current_data[slot] = cached_rows
                self._slot_contracts[slot] = contract
                continue
            if contract.needs_load:
                contract.load(start=start_date, end=end_date)
            self._current_data[slot] = list(contract.data or [])
            self._slot_contracts[slot] = contract

    def rebuild_data_cursor(self) -> None:
        if not self._slot_contracts:
            raise ValueError("当前无可用 contract，无法构建 DataCursor")
        self._cursor_mgr.create_cursor(
            self._cursor_name,
            contracts=self._slot_contracts,
        )

    def preload_klines(
        self, rows: List[Dict[str, Any]], *, start_date: str, end_date: str
    ) -> None:
        contract = self._contract_manager().issue(
            DataKey.STOCK_KLINE,
            entity_id=self.stock_id,
            start=start_date,
            end=end_date,
            term="daily",
        )
        contract.data = list(rows or [])
        self._current_data["klines"] = list(rows or [])
        self._slot_contracts["klines"] = contract

    def load_declared_items(
        self,
        items: List[Dict[str, Any]],
        *,
        start_date: str,
        end_date: str,
    ) -> None:
        st = StrategySettingsView({"data": self.settings.data})
        for raw in items:
            item = self._normalize_declaration_item(st, raw)
            dk = DataKey(str(item["data_id"]))
            params = dict(item.get("params") or {})
            contract = self._contract_manager().issue(
                dk,
                entity_id=self.stock_id,
                start=start_date,
                end=end_date,
                **params,
            )
            slot = self.storage_key_for(dk)
            spec = self._contract_manager().map.get(dk)
            if (
                spec
                and spec.get("scope") == ContractScope.GLOBAL
                and self._global_extra_cache is not None
                and slot in self._global_extra_cache
            ):
                rows = list(self._global_extra_cache[slot])
                contract.data = rows
            else:
                if contract.needs_load:
                    contract.load(start=start_date, end=end_date)
                rows = list(contract.data or [])
            self._current_data[slot] = rows
            self._slot_contracts[slot] = contract

    def load_latest_data(self, lookback: int = None) -> None:
        if lookback is None:
            lookback = self.settings.min_required_records or 100
        latest_date = self._get_latest_trading_date()
        start_date = self._get_date_before(latest_date, lookback)
        self.hydrate_row_slots(start_date, latest_date)
        self.apply_indicators()
        self.rebuild_data_cursor()

    def load_historical_data(self, start_date: str, end_date: str) -> None:
        self._current_data = {"klines": []}
        self._slot_contracts = {}
        self.hydrate_row_slots(start_date, end_date)
        self.apply_indicators()
        self.rebuild_data_cursor()

    def get_klines(self) -> List[Dict[str, Any]]:
        return self._current_data.get("klines", [])

    def get_entity_data(self, entity_type: str) -> List[Dict[str, Any]]:
        return self._current_data.get(entity_type, [])

    def get_loaded_data(self) -> Dict[str, List[Dict[str, Any]]]:
        return {k: list(v or []) for k, v in self._current_data.items()}

    def get_data_until(self, date_of_today: str) -> Dict[str, Any]:
        cursor = self._cursor_mgr.get_cursor(self._cursor_name)
        return cursor.until(date_of_today)

    def apply_indicators(self) -> None:
        indicators_cfg = getattr(self.settings, "indicators", None)
        klines = self._current_data.get("klines") or []
        if not indicators_cfg or not klines:
            return
        for name, configs in indicators_cfg.items():
            if not configs:
                continue
            if not isinstance(configs, list):
                configs = [configs]
            for cfg in configs:
                try:
                    result = IndicatorService.calculate(name, klines, **cfg)
                    if not result:
                        continue
                    if isinstance(result, list):
                        field = self._build_indicator_field_name(name, cfg)
                        for rec, val in zip(klines, result):
                            rec[field] = val
                    elif isinstance(result, dict):
                        for key, series in result.items():
                            field = self._build_indicator_field_name(
                                f"{name}_{key}", cfg
                            )
                            for rec, val in zip(klines, series):
                                rec[field] = val
                except Exception as exc:
                    logger.error(
                        "计算指标失败: stock=%s, indicator=%s, params=%s, error=%s",
                        self.stock_id,
                        name,
                        cfg,
                        exc,
                    )

    def _build_indicator_field_name(self, name: str, params: Dict[str, Any]) -> str:
        name = name.lower()
        period = params.get("period") or params.get("length")
        if period is not None and isinstance(period, (int, float, str)):
            return f"{name}{int(period)}"
        parts = [name]
        for key in sorted(params.keys()):
            value = params[key]
            if isinstance(value, (int, float, str)):
                parts.append(f"{key}{value}")
        return "_".join(parts)

    def _get_latest_trading_date(self) -> str:
        try:
            params = dict(self.settings.resolved_base_required_data.get("params") or {})
            contract = self._contract_manager().issue(
                DataKey.STOCK_KLINE,
                entity_id=self.stock_id,
                start=DateUtils.get_query_date_range_min(),
                end=DateUtils.QUERY_DATE_RANGE_MAX,
                **params,
            )
            rows = contract.load(
                start=DateUtils.get_query_date_range_min(),
                end=DateUtils.QUERY_DATE_RANGE_MAX,
            )
            if rows:
                last = rows[-1]
                if isinstance(last, dict) and last.get("date"):
                    return str(last["date"])
            return datetime.now().strftime("%Y%m%d")
        except Exception:
            return datetime.now().strftime("%Y%m%d")

    def _get_date_before(self, date: str, days: int) -> str:
        try:
            adjusted_days = int(days * 1.5)
            return DateUtils.sub_days(date, adjusted_days)
        except Exception:
            return date

    @staticmethod
    def preload_global_extras_for_enumeration(
        validated_settings: Dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        ss = StrategySettingsView.from_dict(validated_settings)
        extras = ss.extra_required_data_sources
        if not extras:
            return {}

        dcm = DataContractManager(contract_cache=ContractCacheManager())
        out: Dict[str, List[Dict[str, Any]]] = {}

        for raw in extras:
            item = StrategySettingsView.normalize_extra_required_data_item(raw)
            dk = DataKey(str(item["data_id"]))
            spec = dcm.map.get(dk)
            if not spec or spec.get("scope") != ContractScope.GLOBAL:
                continue

            params = dict(item.get("params") or {})
            c = dcm.issue(dk, start=start_date, end=end_date, **params)
            out[storage_key_for(dk)] = list(c.data or [])
        return out


__all__ = ["StrategyDataInjectionService"]
