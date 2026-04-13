"""
Strategy 数据管理。

前半段：契约签发与行表装填（``issue_contracts`` / ``hydrate_row_slots``）。
后半段：自原 ``StrategyWorkerDataManager`` 迁入的运行时能力（Scanner/Simulator 拉数、指标、游标）。
"""

from __future__ import annotations

import datetime as dt
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.indicator import IndicatorService
from core.modules.strategy.models.strategy_settings import StrategySettings

if TYPE_CHECKING:
    from core.modules.data_manager.data_manager import DataManager

logger = logging.getLogger(__name__)


class StrategyDataManager:
    """
    解析 ``settings.data``、签发契约并维护行表 / 游标。

    主进程仅 GLOBAL：``issue_contracts(..., entity_id=None)``；
    子进程单标的：``entity_id=stock_id`` 后 ``hydrate_row_slots``。
    """

    def __init__(
        self,
        stock_id: str,
        settings: StrategySettings,
        data_mgr: "DataManager",
        *,
        contract_cache: ContractCacheManager,
        global_extra_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        self.stock_id = stock_id
        self.settings = settings
        self.data_mgr = data_mgr
        self._global_extra_cache = global_extra_cache
        self._contract_cache = contract_cache
        self._dcf_mgr: Optional[DataContractManager] = None

        self._current_data: Dict[str, List[Dict[str, Any]]] = {"klines": []}
        self._cursor_state: Dict[str, Dict[str, Any]] = {}

    # --- data 契约：签发与行表 hydrate ---

    def _contract_manager(self) -> DataContractManager:
        if self._dcf_mgr is None:
            self._dcf_mgr = DataContractManager(contract_cache=self._contract_cache)
        return self._dcf_mgr

    @staticmethod
    def storage_key_for(data_id: DataKey) -> str:
        """行表槽位名（与 ``DataKey`` 对应）。"""
        if data_id == DataKey.STOCK_KLINE:
            return "klines"
        if data_id == DataKey.TAG:
            return "tags"
        return data_id.value

    def issue_contracts(
        self,
        *,
        start: str,
        end: str,
        entity_id: Optional[str] = None,
        data_block: Optional[Dict[str, Any]] = None,
    ) -> Dict[DataKey, DataContract]:
        """
        根据 ``data`` 块签发契约；默认使用 ``self.settings.data``。

        :param entity_id: 非空时签发 ``PER_ENTITY``；为空则只签发 ``GLOBAL``。
        """
        block = data_block if data_block is not None else self.settings.data
        st = StrategySettings({"data": block})
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
        st: StrategySettings, raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        item = dict(raw)
        dk = DataKey(str(item["data_id"]))
        params = dict(item.get("params") or {})
        if dk == DataKey.TAG:
            if str(params.get("entity_type") or "").strip() == "":
                et = st.tag_storage_entity_type
                if et:
                    params["entity_type"] = str(et)
            item["params"] = params
        return item

    def hydrate_row_slots(self, start_date: str, end_date: str) -> None:
        """按声明 ``issue``，再 ``load`` 尚未物化的契约，写入 ``_current_data``。"""
        self._contract_cache.enter_strategy_run()
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
                self._current_data[slot] = list(self._global_extra_cache[slot])
                continue
            if contract.needs_load:
                contract.load(start=start_date, end=end_date)
            self._current_data[slot] = list(contract.data or [])

    # =========================================================================
    # 以下为原 StrategyWorkerDataManager 路径（枚举器预加载、Scanner/Simulator、指标、游标）
    # =========================================================================

    def _merge_tag_entity_type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(params)
        if str(out.get("entity_type") or "").strip() == "":
            et = getattr(self.settings, "tag_storage_entity_type", None)
            if et:
                out["entity_type"] = str(et)
        return out

    def _load_data_source_item(
        self, item: Dict[str, Any], start_date: str, end_date: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """单条声明（枚举器预加载 K 线后仅拉 extra 等）。"""
        data_id = DataKey(str(item["data_id"]))
        params = dict(item.get("params") or {})
        if data_id == DataKey.TAG:
            params = self._merge_tag_entity_type(params)
        c = self._contract_manager().issue(
            data_id,
            entity_id=self.stock_id,
            start=start_date,
            end=end_date,
            **params,
        )
        if c.needs_load:
            raw = c.load(start=start_date, end=end_date)
        else:
            raw = c.data
        rows = list(raw or [])
        return self.storage_key_for(data_id), rows

    def _materialize_data_source_item(
        self, item: Dict[str, Any], start_date: str, end_date: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        data_id = DataKey(str(item["data_id"]))
        spec = self._contract_manager().map.get(data_id)
        if (
            spec
            and spec.get("scope") == ContractScope.GLOBAL
            and self._global_extra_cache is not None
        ):
            slot = self.storage_key_for(data_id)
            if slot in self._global_extra_cache:
                return slot, list(self._global_extra_cache[slot])
        return self._load_data_source_item(item, start_date, end_date)

    def _init_cursor_state(self) -> None:
        """预加载 K 线后仅为额外依赖初始化游标（与 ``load_historical_data`` 对齐）。"""
        for key, data in self._current_data.items():
            if key == "klines":
                if data:
                    self._cursor_state["klines"] = {"cursor": -1, "acc": []}
                continue
            if key == DataKey.MACRO_GDP.value:
                continue
            if data:
                self._cursor_state[key] = {"cursor": -1, "acc": []}

    def load_latest_data(self, lookback: int = None) -> None:
        if lookback is None:
            lookback = self.settings.min_required_records or 100
        latest_date = self._get_latest_trading_date()
        start_date = self._get_date_before(latest_date, lookback)
        self.hydrate_row_slots(start_date, latest_date)
        klines = self._current_data.get("klines") or []
        self._apply_indicators()
        logger.debug(
            "加载最新数据: stock=%s, records=%s, date_range=%s-%s",
            self.stock_id,
            len(klines),
            start_date,
            latest_date,
        )

    def load_historical_data(self, start_date: str, end_date: str) -> None:
        self._cursor_state.clear()
        self._current_data["klines"] = []
        self.hydrate_row_slots(start_date, end_date)
        klines = self._current_data.get("klines") or []
        logger.debug(
            "加载历史数据: stock=%s, records=%s, date_range=%s-%s",
            self.stock_id,
            len(klines),
            start_date,
            end_date,
        )
        self._apply_indicators()
        self._cursor_state["klines"] = {"cursor": -1, "acc": []}
        for key, data in self._current_data.items():
            if key == "klines":
                continue
            if key == DataKey.MACRO_GDP.value:
                continue
            if data:
                self._cursor_state[key] = {"cursor": -1, "acc": []}

    def get_klines(self) -> List[Dict[str, Any]]:
        return self._current_data.get("klines", [])

    def get_entity_data(self, entity_type: str) -> List[Dict[str, Any]]:
        return self._current_data.get(entity_type, [])

    def get_data_until(self, date_of_today: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        klines = self._current_data.get("klines") or []
        klines_state = self._cursor_state.get("klines")

        if klines and klines_state is not None:
            before_cursor = klines_state.get("cursor", -1)
            acc = klines_state.setdefault("acc", [])
            i = before_cursor + 1
            n = len(klines)
            new_cursor = before_cursor
            while i < n:
                rec = klines[i]
                d = rec.get("date")
                if d is None:
                    i += 1
                    continue
                if d > date_of_today:
                    break
                acc.append(rec)
                new_cursor = i
                i += 1
            klines_state["cursor"] = new_cursor
            result["klines"] = acc

        for entity_type, data in self._current_data.items():
            if entity_type == "klines":
                continue
            if entity_type == DataKey.MACRO_GDP.value:
                result[entity_type] = list(data or [])
                continue
            state = self._cursor_state.get(entity_type)
            if state is None:
                continue
            if entity_type == "tags":
                date_field = "as_of_date"
            elif entity_type == DataKey.STOCK_CORPORATE_FINANCE.value or "finance" in str(
                entity_type
            ).lower():
                date_field = "quarter"
            else:
                date_field = "date"
            before_cursor = state.get("cursor", -1)
            acc = state.setdefault("acc", [])
            i = before_cursor + 1
            n = len(data)
            new_cursor = before_cursor
            while i < n:
                rec = data[i]
                d = rec.get(date_field)
                if d is None:
                    i += 1
                    continue
                d_norm = self._normalize_date_value(d)
                if d_norm is None:
                    i += 1
                    continue
                if d_norm > date_of_today:
                    break
                acc.append(rec)
                new_cursor = i
                i += 1
            state["cursor"] = new_cursor
            result[entity_type] = acc
        return result

    @staticmethod
    def _normalize_date_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, dt.datetime):
            return value.strftime("%Y%m%d")
        if isinstance(value, dt.date):
            return value.strftime("%Y%m%d")
        if isinstance(value, str):
            return value.strip()
        return None

    def _apply_indicators(self) -> None:
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
                    if name.lower() == "ma":
                        length = cfg.get("period") or cfg.get("length")
                        if not length:
                            continue
                        values = IndicatorService.ma(klines, length=int(length))
                        if not values:
                            continue
                        field = f"ma{length}"
                        for rec, val in zip(klines, values):
                            rec[field] = val
                    elif name.lower() == "ema":
                        length = cfg.get("period") or cfg.get("length")
                        if not length:
                            continue
                        values = IndicatorService.ema(klines, length=int(length))
                        if not values:
                            continue
                        field = f"ema{length}"
                        for rec, val in zip(klines, values):
                            rec[field] = val
                    elif name.lower() == "rsi":
                        length = cfg.get("period") or cfg.get("length")
                        if not length:
                            continue
                        values = IndicatorService.rsi(klines, length=int(length))
                        if not values:
                            continue
                        field = f"rsi{length}"
                        for rec, val in zip(klines, values):
                            rec[field] = val
                    elif name.lower() == "macd":
                        fast = cfg.get("fast", 12)
                        slow = cfg.get("slow", 26)
                        signal = cfg.get("signal", 9)
                        result = IndicatorService.macd(
                            klines, fast=int(fast), slow=int(slow), signal=int(signal)
                        )
                        if not result:
                            continue
                        for key, series in result.items():
                            for rec, val in zip(klines, series):
                                rec[key] = val
                    else:
                        result = IndicatorService.calculate(name, klines, **cfg)
                        if not result:
                            continue
                        if isinstance(result, list):
                            field = self._build_indicator_field_name(name, cfg)
                            for rec, val in zip(klines, result):
                                rec[field] = val
                        elif isinstance(result, dict):
                            for key, series in result.items():
                                field = self._build_indicator_field_name(f"{name}_{key}", cfg)
                                for rec, val in zip(klines, series):
                                    rec[field] = val
                except Exception as e:
                    logger.error(
                        "计算指标失败: stock=%s, indicator=%s, params=%s, error=%s",
                        self.stock_id,
                        name,
                        cfg,
                        e,
                    )

    def _build_indicator_field_name(self, name: str, params: Dict[str, Any]) -> str:
        name = name.lower()
        period = params.get("period") or params.get("length")
        if period is not None and isinstance(period, (int, float, str)):
            return f"{name}{int(period)}"
        parts = [name]
        for k in sorted(params.keys()):
            v = params[k]
            if isinstance(v, (int, float, str)):
                parts.append(f"{k}{v}")
        return "_".join(parts)

    def _get_latest_trading_date(self) -> str:
        try:
            latest_kline = self.data_mgr.stock.kline.load_latest(self.stock_id)
            if latest_kline:
                return latest_kline["date"]
            logger.warning("无法获取最新交易日，使用当前日期: stock=%s", self.stock_id)
            return datetime.now().strftime("%Y%m%d")
        except Exception as e:
            logger.error("获取最新交易日失败: stock=%s, error=%s", self.stock_id, e)
            return datetime.now().strftime("%Y%m%d")

    def _get_date_before(self, date: str, days: int) -> str:
        from core.utils.date.date_utils import DateUtils

        try:
            adjusted_days = int(days * 1.5)
            return DateUtils.sub_days(date, adjusted_days)
        except Exception as e:
            logger.error("计算日期失败: date=%s, days=%s, error=%s", date, days, e)
            return date
