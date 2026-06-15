#!/usr/bin/env python3
"""
策略侧 **contract 注入** 服务。

**范围（决策 11）** — 仅处理用户在 ``settings.data`` 中声明的数据：

- ``base_required_data`` + ``extra_required_data_sources`` → ``required_data_sources``
- 经 ``DataContractManager.issue`` / ``StrategyJobContractBatch`` 物化后装入 slot 与 ``DataCursor``

**不在此服务内、由回测编排直调 DataManager 的示例：**

- 股票池 / PIT universe（``stock.list.load``）
- 单票元数据（``load_meta`` / ``load_single``）
- 交易日历、最新已完成交易日

若用户将 ``stock.list`` 等写入 ``extra_required_data_sources``，则纳入本服务与 contract 路径。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler

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
from core.modules.strategy.services.data.injection.job_contract_batch import (
    StrategyJobContractBatch,
)
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)

class StrategyDataInjectionService:
    """为单股 worker 装填 **settings 已声明** 的 contract 数据（见模块 docstring）。"""

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

        self._current_data: Dict[str, List[Dict[str, Any]]] = {}
        self._slot_contracts: Dict[str, DataContract] = {}
        self._cursor_mgr = DataCursorManager()
        self._cursor_name = f"strategy:{self.stock_id}"
        self._load_profiler: Optional["PerformanceProfiler"] = None

    def attach_load_profiler(self, profiler: Optional["PerformanceProfiler"]) -> None:
        """可选：记录 contract.load 墙钟（storage / DB 读取）。"""
        self._load_profiler = profiler

    def _record_contract_load(self, slot: str, load_fn) -> None:
        if self._load_profiler is None:
            load_fn()
            return
        t0 = time.perf_counter()
        load_fn()
        self._load_profiler.record_storage_load(slot, time.perf_counter() - t0)

    def _contract_manager(self) -> DataContractManager:
        if self._dcf_mgr is None:
            self._dcf_mgr = DataContractManager(contract_cache=self._contract_cache)
        return self._dcf_mgr

    @staticmethod
    def storage_key_for(data_id: DataKey, *, is_base: bool = False) -> str:
        return storage_key_for(data_id, is_base=is_base)

    def _base_data_key(self, st: Optional[StrategySettingsView] = None) -> DataKey:
        view = st if st is not None else self.settings
        normalized = StrategySettingsView.normalize_base_required_data(view.base_required_data)
        return DataKey(str(normalized["data_id"]))

    def _slot_for_contract(
        self,
        dk: DataKey,
        *,
        st: Optional[StrategySettingsView] = None,
    ) -> str:
        is_base = dk == self._base_data_key(st)
        return self.storage_key_for(dk, is_base=is_base)

    def issue_contracts(
        self,
        *,
        start: str,
        end: str,
        entity_id: Optional[str] = None,
        entity_ids: Optional[Sequence[str]] = None,
        data_block: Optional[Dict[str, Any]] = None,
    ) -> Dict[DataKey, DataContract]:
        block = data_block if data_block is not None else self.settings.data
        st = StrategySettingsView({"data": block})
        declarations = st.required_data_sources

        if entity_id is not None and entity_ids is not None:
            raise ValueError("issue_contracts：entity_id 与 entity_ids 互斥")

        if entity_ids is not None:
            ids = [str(x).strip() for x in entity_ids if str(x).strip()]
            if not ids:
                raise ValueError("issue_contracts：entity_ids 不能为空")
            batch = StrategyJobContractBatch.hydrate(
                entity_ids=ids,
                settings=st,
                start=start,
                end=end,
                contract_cache=self._contract_cache,
                global_extra_cache=self._global_extra_cache,
            )
            if len(ids) == 1:
                return batch.contracts_for_entity(ids[0])
            raise ValueError(
                "issue_contracts 仅支持单 entity；多 entity 请用 StrategyJobContractBatch.hydrate"
            )

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

            if scope == ContractScope.PER_ENTITY:
                contract = dcm.issue(
                    dk,
                    entity_ids=[eff_entity],
                    start=start,
                    end=end,
                    **params,
                ).require_contract(entity_id=eff_entity)
            else:
                contract = dcm.issue(
                    dk,
                    start=start,
                    end=end,
                    **params,
                ).require_contract()
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

    def clear_working_state(self) -> None:
        """释放当前股槽位与 cursor（同 job 内处理下一股前调用）。"""
        self._current_data = {}
        self._slot_contracts = {}
        try:
            self._cursor_mgr.drop_cursor(self._cursor_name)
        except Exception:
            pass

    def _apply_contracts_to_slots(
        self,
        contracts: Dict[DataKey, DataContract],
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        settings_view: Optional[StrategySettingsView] = None,
    ) -> None:
        dcm = self._contract_manager()
        st = settings_view or self.settings
        self._slot_contracts = {}
        self._current_data = {}
        for dk, contract in contracts.items():
            spec = dcm.map.get(dk)
            slot = self._slot_for_contract(dk, st=st)
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
            if contract.needs_load and start_date is not None and end_date is not None:
                self._record_contract_load(
                    slot,
                    lambda c=contract, s=start_date, e=end_date: c.load(start=s, end=e),
                )
            self._current_data[slot] = list(contract.data or [])
            self._slot_contracts[slot] = contract

    def adopt_job_batch(
        self,
        batch: StrategyJobContractBatch,
    ) -> None:
        """从 job 级 batch issue 装填当前 ``stock_id`` 的 slot（不再触库）。"""
        contracts = batch.contracts_for_entity(self.stock_id)
        self._apply_contracts_to_slots(contracts)

    def hydrate_row_slots(
        self,
        start_date: str,
        end_date: str,
        *,
        fresh_strategy_cache: bool = True,
    ) -> None:
        if fresh_strategy_cache:
            self._contract_cache.enter_strategy_run()
        contracts = self.issue_contracts(
            start=start_date,
            end=end_date,
            entity_id=self.stock_id,
        )
        self._apply_contracts_to_slots(contracts, start_date=start_date, end_date=end_date)

    def rebuild_data_cursor(self) -> None:
        if not self._slot_contracts:
            raise ValueError("当前无可用 contract，无法构建 DataCursor")
        self._cursor_mgr.create_cursor(
            self._cursor_name,
            contracts=self._slot_contracts,
        )

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
            spec = self._contract_manager().map.get(dk)
            if spec and spec.get("scope") == ContractScope.PER_ENTITY:
                contract = self._contract_manager().issue(
                    dk,
                    entity_ids=[self.stock_id],
                    start=start_date,
                    end=end_date,
                    **params,
                ).require_contract()
            else:
                contract = self._contract_manager().issue(
                    dk,
                    start=start_date,
                    end=end_date,
                    **params,
                ).require_contract()
            slot = self._slot_for_contract(dk)
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
                    self._record_contract_load(
                        slot,
                        lambda c=contract, s=start_date, e=end_date: c.load(start=s, end=e),
                    )
                rows = list(contract.data or [])
            self._current_data[slot] = rows
            self._slot_contracts[slot] = contract

    def load_latest_data(self, lookback: int = None) -> None:
        if lookback is None:
            lookback = self.settings.min_required_records or 100
        latest_date = self._get_latest_completed_trading_date()
        start_date = self._get_date_before(latest_date, lookback)
        self.hydrate_row_slots(start_date, latest_date)
        self.apply_indicators()
        self.rebuild_data_cursor()

    def load_historical_data(self, start_date: str, end_date: str) -> None:
        self._current_data = {}
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
        st = self.settings
        base_dk = self._base_data_key(st)
        for raw in st.required_data_sources:
            item = self._normalize_declaration_item(st, raw)
            indicators_cfg = StrategySettingsView.normalize_indicators(item.get("indicators"))
            if not indicators_cfg:
                continue
            dk = DataKey(str(item["data_id"]))
            slot = self.storage_key_for(dk, is_base=(dk == base_dk))
            rows = self._current_data.get(slot) or []
            if not rows:
                continue
            self._apply_indicators_to_rows(rows, indicators_cfg)

    def _apply_indicators_to_rows(
        self,
        rows: List[Dict[str, Any]],
        indicators_cfg: Dict[str, Any],
    ) -> None:
        for name, cfg, result in IndicatorService.compute_batch(rows, indicators_cfg):
            try:
                if isinstance(result, list):
                    field = self._build_indicator_field_name(name, cfg)
                    for rec, val in zip(rows, result):
                        rec[field] = val
                elif isinstance(result, dict):
                    for key, series in result.items():
                        field = self._build_indicator_field_name(f"{name}_{key}", cfg)
                        for rec, val in zip(rows, series):
                            rec[field] = val
            except Exception as exc:
                logger.error(
                    "写入指标失败: stock=%s, indicator=%s, params=%s, error=%s",
                    self.stock_id,
                    name,
                    cfg,
                    exc,
                )

    def _build_indicator_field_name(self, name: str, params: Dict[str, Any]) -> str:
        name = name.lower()
        length = params.get("length")
        if length is not None and isinstance(length, (int, float, str)):
            return f"{name}{int(length)}"
        parts = [name]
        for key in sorted(params.keys()):
            value = params[key]
            if isinstance(value, (int, float, str)):
                parts.append(f"{key}{value}")
        return "_".join(parts)

    def _get_latest_completed_trading_date(self) -> str:
        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_latest_completed_trading_date,
        )

        dm = DataManager(is_verbose=False)
        if dm is None:
            return ""
        return resolve_latest_completed_trading_date(dm)

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
            c = dcm.issue(dk, start=start_date, end=end_date, **params).require_contract()
            out[storage_key_for(dk, is_base=False)] = list(c.data or [])
        return out


__all__ = ["StrategyDataInjectionService"]
