#!/usr/bin/env python3
"""
Strategy Worker Data Manager - 策略数据管理器

职责：
- 加载当前股票的 K-line、财务等数据
- 提供数据访问接口
- 数据生命周期：仅存在于当前 Worker 实例中

重要：
- ✅ ``ContractScope.GLOBAL`` 的非时序 / 时序物化由 ``DataContractManager.issue`` 走进程内 contract 缓存（两层：global / per-run），见 ``data_contract.cache`` 与 ``DECISIONS.md``
- ✅ 主进程预加载的 GLOBAL extra 仍可通过 ``global_extra_cache`` 传入（枚举器 MVP：opt1 pickle），优先于再拉数
- ❌ ``PER_ENTITY`` 等不在上述缓存策略内，仍直走 loader；大表仍在子进程按声明加载
- 📝 当前股票行数据存放在 Worker 实例字段中，Worker 销毁时释放

类比 TagWorkerDataManager
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING, Tuple
from datetime import datetime, timedelta
import datetime as dt
import logging

from core.modules.indicator import IndicatorService
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager

if TYPE_CHECKING:
    from core.modules.strategy.models.strategy_settings import StrategySettings
    from core.modules.data_manager.data_manager import DataManager

logger = logging.getLogger(__name__)


class StrategyWorkerDataManager:
    """
    策略数据管理器（Worker 级别）
    
    重要说明：
    - 此类只管理【当前股票】的数据
    - 数据存储在 Worker 实例中，不是全局缓存
    - Worker 执行完毕后，实例销毁，数据自动清理
    - 通过限制 Worker 数量控制内存使用
    """
    
    def __init__(
        self,
        stock_id: str,
        settings: 'StrategySettings',
        data_mgr: 'DataManager',
        *,
        contract_cache: ContractCacheManager,
        global_extra_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ):
        """
        初始化数据管理器
        
        Args:
            stock_id: 股票代码
            settings: 策略配置
            data_mgr: DataManager 实例
            contract_cache: 进程内 contract 缓存（与 ``DataContractManager`` 共用）
            global_extra_cache: 主进程已加载的 GLOBAL extra（槽位 key → rows）；未传则 GLOBAL 也在本进程加载
        """
        self.stock_id = stock_id
        self.settings = settings
        self.data_mgr = data_mgr
        self._global_extra_cache: Optional[Dict[str, List[Dict[str, Any]]]] = global_extra_cache
        self._contract_cache = contract_cache
        
        # 当前股票的原始数据存储（Scanner 使用，NOT 缓存！）
        # - Scan 模式：使用 _current_data 提供 List[Dict] 给扫描器
        # - Simulate / 枚举模式：不依赖 _current_data，只使用列式 TimeSeriesData
        self._current_data: Dict[str, List[Dict[str, Any]]] = {
            "klines": [],
            # 其他数据类型...
        }

        # 游标累积状态（用于 List[Dict] 累积）
        self._cursor_state: Dict[str, Dict[str, Any]] = {}
        self._dcf_mgr: Optional[DataContractManager] = None

    def _contract_manager(self) -> DataContractManager:
        if self._dcf_mgr is None:
            self._dcf_mgr = DataContractManager(contract_cache=self._contract_cache)
        return self._dcf_mgr

    @staticmethod
    def _storage_key_for(data_id: DataKey) -> str:
        if data_id == DataKey.STOCK_KLINE:
            return "klines"
        if data_id == DataKey.TAG:
            return "tags"
        return data_id.value

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
        """通过 DataContractManager 加载一项声明，返回 ``(存储槽位 key, rows)``。"""
        data_id = DataKey(str(item["data_id"]))
        params = dict(item.get("params") or {})
        if data_id == DataKey.TAG:
            params = self._merge_tag_entity_type(params)
        ctx = {"stock_id": self.stock_id}
        c = self._contract_manager().issue(
            data_id,
            entity_id=self.stock_id,
            start=start_date,
            end=end_date,
            **params,
        )
        if c.data is not None:
            raw = c.data
        else:
            raw = c.load(start=start_date, end=end_date)
        rows = list(raw or [])
        return self._storage_key_for(data_id), rows

    def _materialize_data_source_item(
        self, item: Dict[str, Any], start_date: str, end_date: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        加载单条声明：GLOBAL 且主进程已提供 ``global_extra_cache`` 时直接使用缓存行（只读副本）；
        否则走 ``DataContractManager``（子进程查库）。
        """
        data_id = DataKey(str(item["data_id"]))
        spec = self._contract_manager().map.get(data_id)
        if (
            spec
            and spec.get("scope") == ContractScope.GLOBAL
            and self._global_extra_cache is not None
        ):
            slot = self._storage_key_for(data_id)
            if slot in self._global_extra_cache:
                return slot, list(self._global_extra_cache[slot])
        return self._load_data_source_item(item, start_date, end_date)

    def _init_cursor_state(self) -> None:
        """在预加载 K 线后仅为「额外依赖」初始化游标（与 ``load_historical_data`` 语义对齐）。"""
        for key, data in self._current_data.items():
            if key == "klines":
                if data:
                    self._cursor_state["klines"] = {"cursor": -1, "acc": []}
                continue
            if key == DataKey.MACRO_GDP.value:
                continue
            if data:
                self._cursor_state[key] = {"cursor": -1, "acc": []}

    # =========================================================================
    # Scanner 数据加载
    # =========================================================================
    
    def load_latest_data(self, lookback: int = None):
        """
        加载最新数据（Scanner 使用）
        
        Args:
            lookback: 历史窗口天数（如果不指定，使用 settings 中的配置）
        
        流程：
        1. 获取最新交易日
        2. 计算开始日期（latest_date - lookback）
        3. 加载 K-line
        4. 加载其他数据（根据 ``required_data_sources``，经 DataContractManager）
        """
        # 1. 确定 lookback
        if lookback is None:
            lookback = self.settings.min_required_records or 100
        
        # 2. 获取最新交易日
        latest_date = self._get_latest_trading_date()
        
        # 3. 计算开始日期（使用 lookback 天数）
        start_date = self._get_date_before(latest_date, lookback)

        # 4. 按声明加载（主依赖 + 额外依赖）；与 simulate 一致，清空 per-run 层再装填
        self._contract_cache.enter_strategy_run()
        for item in self.settings.required_data_sources:
            slot, rows = self._materialize_data_source_item(item, start_date, latest_date)
            self._current_data[slot] = rows

        klines = self._current_data.get("klines") or []

        # 4.1 计算技术指标（仅基于 K 线，一次性完成）
        self._apply_indicators()
        
        logger.debug(
            "加载最新数据: stock=%s, records=%s, date_range=%s-%s",
            self.stock_id,
            len(klines),
            start_date,
            latest_date,
        )
    
    # =========================================================================
    # Simulator 数据加载
    # =========================================================================
    
    def load_historical_data(self, start_date: str, end_date: str):
        """
        加载历史数据（Simulator / Enumerator 使用）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        流程：
        1. 加载全量 K-line（从 start_date 到 end_date）
        2. 计算技术指标（行式 List[Dict] 上直接计算）
        3. 为枚举器初始化游标状态（_cursor_state + _current_data）
        4. 可选：构建列式 TimeSeriesData（_ts_data），供后续模块使用
        
        注意：这里加载全量数据，后续通过游标逐日过滤，避免每次切片复制。
        """
        # 0. 清空旧的数据结构
        self._cursor_state.clear()
        self._current_data["klines"] = []

        # 1. 按声明加载主依赖与额外依赖（行式）；清空 per-run 缓存层，避免沿用上一段区间
        self._contract_cache.enter_strategy_run()
        for item in self.settings.required_data_sources:
            slot, rows = self._materialize_data_source_item(item, start_date, end_date)
            self._current_data[slot] = rows

        klines = self._current_data.get("klines") or []

        logger.debug(
            "加载历史数据: stock=%s, records=%s, date_range=%s-%s",
            self.stock_id,
            len(klines),
            start_date,
            end_date,
        )

        # 1.1 计算技术指标（仅基于 K 线，一次性完成，直接写回 klines）
        self._apply_indicators()

        # 1.2 初始化游标累积状态（为 Enumerator 提供“截至今日”的 List[Dict] 视图）
        self._cursor_state["klines"] = {"cursor": -1, "acc": []}

        for key, data in self._current_data.items():
            if key == "klines":
                continue
            if key == DataKey.MACRO_GDP.value:
                continue
            if data:
                self._cursor_state[key] = {"cursor": -1, "acc": []}
    
    # =========================================================================
    # 数据访问接口
    # =========================================================================
    
    def get_klines(self):
        """
        获取当前股票的 K-line 数据
        
        Scan / Enumerator 模式：
            - 返回 List[Dict]（来自 _current_data['klines']）
        说明：
            - 列式 TimeSeriesData 存放在 self._ts_data 中，供后续模块按需使用
        """
        return self._current_data.get("klines", [])
    
    def get_entity_data(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        获取当前股票的其他实体数据
        
        注意：这不是缓存，只是当前 Worker 实例的临时数据
        
        Args:
            entity_type: 数据类型（如 'corporate_finance'）
        
        Returns:
            data: [...]
        """
        return self._current_data.get(entity_type, [])
    
    # =========================================================================
    # 游标机制（Simulator 逐日遍历使用）
    # =========================================================================
    
    def get_data_until(self, date_of_today: str) -> Dict[str, Any]:
        """
        使用游标获取指定日期（含）之前的所有数据
        
        核心思想:
        - 维护每类数据的游标位置（cursor）和累积数据（acc）
        - 每次调用只 append 新增的数据，不重新切片
        - 对调用方暴露“截至 date_of_today 的前缀视图”（List[Dict]），语义与旧实现保持一致
        
        Args:
            date_of_today: 当前虚拟日期（YYYYMMDD）
        
        Returns:
            data_of_today: {
                'klines': [...],              # List[Dict]，日期 <= date_of_today
                'tags': [...],
                'corporate_finance': [...],
                ...
            }
        """
        result: Dict[str, Any] = {}

        # 1. 处理 K 线数据（基于 _current_data['klines'] + 游标累积）
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

        # 2. 处理其他数据类型（tags / corporate_finance 等）
        for entity_type, data in self._current_data.items():
            if entity_type == "klines":
                continue

            if entity_type == DataKey.MACRO_GDP.value:
                result[entity_type] = list(data or [])
                continue

            state = self._cursor_state.get(entity_type)
            if state is None:
                continue

            # 其他数据类型的时间字段约定：
            # - tags: 使用 as_of_date（TagDataService 返回字段）
            # - corporate_finance: 使用 quarter（兼容旧实现）
            # - 其余：默认使用 date
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

                # DB 返回的日期字段（例如 tag.as_of_date）可能是 datetime.date/datetime.datetime；
                # 这里统一转换为 YYYYMMDD 字符串后再比较，避免类型错误。
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
        """
        将各种可能的日期值归一化为 YYYYMMDD 字符串，便于与 date_of_today 进行比较。

        支持：
        - datetime.date / datetime.datetime -> strftime('%Y%m%d')
        - 'YYYYMMDD' -> 原样返回
        - 其他 -> None（调用方跳过该记录）
        """
        if value is None:
            return None
        if isinstance(value, dt.datetime):
            return value.strftime("%Y%m%d")
        if isinstance(value, dt.date):
            return value.strftime("%Y%m%d")
        if isinstance(value, str):
            v = value.strip()
            # quarter 等格式（YYYYQn）在当前实现中只用于 finance 分支；
            # 对其它数据（如 tags）我们期望是 YYYYMMDD。
            return v
        return None
    
    # =========================================================================
    # 私有方法
    # =========================================================================

    def _apply_indicators(self) -> None:
        """
        根据 settings.data.indicators 使用 IndicatorService 计算指标，
        并将结果直接写回到 K 线字典中。

        重要：
        - 在子进程中对“单只股票 + 整个时间区间”一次性计算
        - 后续通过 get_data_until(date) 游标切片时，只会看到 date 之前的数据，避免上帝模式
        """
        indicators_cfg = getattr(self.settings, "indicators", None)
        klines = self._current_data.get("klines") or []

        if not indicators_cfg or not klines:
            return

        for name, configs in indicators_cfg.items():
            if not configs:
                continue
            # 统一为列表
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
                        # 统一使用 rsi{length} 作为字段名（例如 rsi14），保持与其他指标（ma5, ma10）命名一致
                        field = f"rsi{length}"
                        for rec, val in zip(klines, values):
                            rec[field] = val

                    elif name.lower() == "macd":
                        # macd 返回 dict: {'macd': [...], 'macds': [...], 'macdh': [...]}
                        fast = cfg.get("fast", 12)
                        slow = cfg.get("slow", 26)
                        signal = cfg.get("signal", 9)
                        result = IndicatorService.macd(klines, fast=int(fast), slow=int(slow), signal=int(signal))
                        if not result:
                            continue
                        for key, series in result.items():
                            # 字段名如 macd, macds, macdh
                            for rec, val in zip(klines, series):
                                rec[key] = val

                    else:
                        # 通用入口：IndicatorService.calculate
                        result = IndicatorService.calculate(name, klines, **cfg)
                        if not result:
                            continue
                        # 单列：直接生成一个字段名
                        if isinstance(result, list):
                            field = self._build_indicator_field_name(name, cfg)
                            for rec, val in zip(klines, result):
                                rec[field] = val
                        # 多列：result 是 dict[str, list]
                        elif isinstance(result, dict):
                            for key, series in result.items():
                                field = self._build_indicator_field_name(f"{name}_{key}", cfg)
                                for rec, val in zip(klines, series):
                                    rec[field] = val
                except Exception as e:
                    logger.error(f"计算指标失败: stock={self.stock_id}, indicator={name}, params={cfg}, error={e}")

    def _build_indicator_field_name(self, name: str, params: Dict[str, Any]) -> str:
        """
        根据指标名和参数生成一个简洁可读的字段名。

        约定（尽量与设计文档保持一致）：
        - ma + period=5   -> ma5
        - rsi + period=14 -> rsi14
        - 其他：name_keyValueKeyValue... （例如 cci_len20 -> cci20）
        """
        name = name.lower()
        period = params.get("period") or params.get("length")
        if period is not None and isinstance(period, (int, float, str)):
            return f"{name}{int(period)}"

        # 无明显 period 时，退化为 name 加上关键参数的摘要
        parts = [name]
        for k in sorted(params.keys()):
            v = params[k]
            if isinstance(v, (int, float, str)):
                parts.append(f"{k}{v}")
        return "_".join(parts)
    
    def _get_latest_trading_date(self) -> str:
        """
        获取最新交易日
        
        Returns:
            latest_date: 最新交易日（YYYYMMDD）
        """
        try:
            # 尝试获取最新K线数据
            latest_kline = self.data_mgr.stock.kline.load_latest(self.stock_id)
            if latest_kline:
                return latest_kline['date']
            
            # 如果没有数据，返回当前日期
            logger.warning(f"无法获取最新交易日，使用当前日期: stock={self.stock_id}")
            return datetime.now().strftime('%Y%m%d')
        
        except Exception as e:
            logger.error(f"获取最新交易日失败: stock={self.stock_id}, error={e}")
            return datetime.now().strftime('%Y%m%d')
    
    def _get_date_before(self, date: str, days: int) -> str:
        """
        获取 N 天前的日期（自然日，简化版）
        
        Note: 这里使用自然日计算，确保获取足够的数据
              实际加载时会自动过滤非交易日
        
        Args:
            date: 基准日期（YYYYMMDD）
            days: 天数
        
        Returns:
            earlier_date: N 天前的日期（YYYYMMDD）
        """
        from core.utils.date.date_utils import DateUtils
        try:
            # 使用自然日 * 1.5 倍，确保有足够的交易日数据
            adjusted_days = int(days * 1.5)
            return DateUtils.sub_days(date, adjusted_days)
        
        except Exception as e:
            logger.error(f"计算日期失败: date={date}, days={days}, error={e}")
            return date
    
