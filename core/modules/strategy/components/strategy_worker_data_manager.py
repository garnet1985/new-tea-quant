#!/usr/bin/env python3
"""
Strategy Worker Data Manager - 策略数据管理器

职责：
- 加载当前股票的 K-line、财务等数据
- 提供数据访问接口
- 数据生命周期：仅存在于当前 Worker 实例中

重要：不缓存股票级别的数据！
- ✅ 全局缓存（在 StrategyManager 中）：stock_list, GDP, LPR 等宏观数据
- ❌ 不缓存股票数据：K线、财务数据等（内存占用大）
- 📝 当前股票数据存储在 Worker 实例中，Worker 销毁时自动清理

类比 TagWorkerDataManager
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import datetime as dt
import logging

from core.modules.indicator import IndicatorService

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
    
    def __init__(self, stock_id: str, settings: 'StrategySettings', data_mgr: 'DataManager'):
        """
        初始化数据管理器
        
        Args:
            stock_id: 股票代码
            settings: 策略配置
            data_mgr: DataManager 实例
        """
        self.stock_id = stock_id
        self.settings = settings
        self.data_mgr = data_mgr
        
        # 当前股票的原始数据存储（Scanner 使用，NOT 缓存！）
        # - Scan 模式：使用 _current_data 提供 List[Dict] 给扫描器
        # - Simulate / 枚举模式：不依赖 _current_data，只使用列式 TimeSeriesData
        self._current_data: Dict[str, List[Dict[str, Any]]] = {
            "klines": [],
            # 其他数据类型...
        }

        # 游标累积状态（用于 List[Dict] 累积）
        self._cursor_state: Dict[str, Dict[str, Any]] = {}
    
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
        4. 加载其他数据（根据 settings.required_entities）
        """
        # 1. 确定 lookback
        if lookback is None:
            lookback = self.settings.min_required_records or 100
        
        # 2. 获取最新交易日
        latest_date = self._get_latest_trading_date()
        
        # 3. 计算开始日期（使用 lookback 天数）
        start_date = self._get_date_before(latest_date, lookback)
        
        # 4. 加载 K-line
        term = self._extract_term_from_kline_base(self.settings.base_kline_type)
        adjust = self.settings.adjust_type
        
        klines = self._load_klines(start_date, latest_date, term, adjust)
        self._current_data['klines'] = klines

        # 4.1 计算技术指标（仅基于 K 线，一次性完成）
        self._apply_indicators()
        
        logger.debug(f"加载最新数据: stock={self.stock_id}, term={term}, "
                    f"records={len(klines)}, date_range={start_date}-{latest_date}")
        
        # 5. 加载其他依赖数据（也是临时存储，不缓存）
        for entity_config in self.settings.required_entities:
            entity_type = entity_config.get('type') if isinstance(entity_config, dict) else entity_config
            data = self._load_entity(entity_config, start_date, latest_date)
            # tags：统一放到 result['tags']，避免上层需要关心 EntityType.TAG_SCENARIO 的具体字符串
            if entity_type and 'tag' in str(entity_type).lower():
                self._current_data["tags"] = data
            else:
                self._current_data[entity_type] = data
    
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
        
        # 1. 加载全量 K-line（行式），用于计算指标和游标切片
        term = self._extract_term_from_kline_base(self.settings.base_kline_type)
        adjust = self.settings.adjust_type
        
        klines = self._load_klines(start_date, end_date, term, adjust)

        logger.debug(f"加载历史数据: stock={self.stock_id}, term={term}, "
                    f"records={len(klines)}, date_range={start_date}-{end_date}")
        
        # 1.1 计算技术指标（仅基于 K 线，一次性完成，直接写回 klines）
        # 使用 _current_data['klines'] 以复用指标实现
        self._current_data["klines"] = klines
        self._apply_indicators()

        # 1.2 初始化游标累积状态（为 Enumerator 提供“截至今日”的 List[Dict] 视图）
        self._cursor_state["klines"] = {"cursor": -1, "acc": []}

        # 2. 加载其他依赖数据（全量，行式 -> 游标视图）
        for entity_config in self.settings.required_entities:
            entity_type = entity_config.get('type') if isinstance(entity_config, dict) else entity_config
            data = self._load_entity(entity_config, start_date, end_date)
            
            # 2.1 为 Enumerator 保留行式数据 + 游标状态
            if entity_type and 'tag' in str(entity_type).lower():
                self._current_data["tags"] = data
                self._cursor_state["tags"] = {"cursor": -1, "acc": []}
            else:
                self._current_data[entity_type] = data
                self._cursor_state[entity_type] = {"cursor": -1, "acc": []}
    
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

            state = self._cursor_state.get(entity_type)
            if state is None:
                continue

            # 其他数据类型的时间字段约定：
            # - tags: 使用 as_of_date（TagDataService 返回字段）
            # - corporate_finance: 使用 quarter（兼容旧实现）
            # - 其余：默认使用 date
            if entity_type == "tags":
                date_field = "as_of_date"
            else:
                date_field = "quarter" if "finance" in str(entity_type).lower() else "date"

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
    
    def _load_klines(
        self, 
        start_date: str, 
        end_date: str, 
        term: str,
        adjust: str = 'qfq'
    ) -> List[Dict[str, Any]]:
        """
        加载 K-line 数据（使用 DataManager API）
        
        Args:
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            term: 周期（daily/weekly/monthly）
            adjust: 复权方式（qfq/hfq/none）
        
        Returns:
            klines: [{'date': '20251219', 'open': 10.0, 'close': 10.5, ...}, ...]
        """
        try:
            # 使用 DataManager 的 K线服务加载接口
            klines = self.data_mgr.stock.kline.load(
                stock_id=self.stock_id,
                term=term,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
                filter_negative=True,
                as_dataframe=False  # 返回 List[Dict]
            )
            
            return klines if klines else []

        except Exception as e:
            logger.error(f"加载K线数据失败: stock={self.stock_id}, term={term}, "
                        f"date_range={start_date}-{end_date}, error={e}")
            return []
    
    def _load_entity(
        self, 
        entity_config: Any, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        加载其他实体数据
        
        Args:
            entity_config: 实体配置（字典或字符串）
                - 如果是字典：{'type': 'xxx', 'name': 'xxx', ...}
                - 如果是字符串：'xxx'
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            data: [...]
        """
        # 解析配置
        if isinstance(entity_config, dict):
            entity_type = entity_config.get("type")
            entity_name = entity_config.get("name")
            required = bool(entity_config.get("required", True))
        else:
            entity_type = entity_config
            entity_name = None
            required = True

        entity_type_str = str(entity_type or "")
        try:
            # 根据 entity_type 加载不同的数据
            if "tag" in entity_type_str.lower():
                # 加载 Tag 数据（若声明依赖，则默认 required=True，缺失应 fail-fast）
                return self._load_tag_data(
                    scenario_name=entity_name,
                    start_date=start_date,
                    end_date=end_date,
                    required=required,
                )

            if "corporate_finance" in entity_type_str.lower():
                return self._load_finance_data(start_date, end_date)

            if "gdp" in entity_type_str.lower():
                return self._load_macro_data("sys_gdp", start_date, end_date)

            logger.warning(f"未知的实体类型: {entity_type_str}")
            return []
        except Exception as e:
            # 对 required 数据源，直接抛出，让上层在 preprocess/取数阶段中断
            if required:
                raise
            logger.error(f"加载实体数据失败(已忽略): type={entity_config}, error={e}")
            return []
    
    def _load_tag_data(
        self,
        scenario_name: str,
        start_date: str,
        end_date: str,
        required: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        加载 Tag 数据（基于 TagDataService，按 scenario 维度） 

        约定：
        - 策略配置中的 required_entities 对于 Tag 只暴露 scenario：
            {
                "type": EntityType.TAG_SCENARIO.value,
                "name": "<scenario_name>"
            }
        - 因此此处的参数 scenario_name 实际上来自 entity_config["name"]
        - 不支持在策略侧单独按某个标签名称加载，只能一次性加载该 scenario 下的所有标签值
        """
        if not scenario_name:
            if required:
                raise RuntimeError("策略声明依赖 Tag 场景，但未提供 scenario_name")
            logger.warning("加载 Tag 数据时未提供 scenario_name，返回空结果")
            return []

        # 通过 DataManager 的 stock.tags（TagDataService）加载
        tag_service = getattr(self.data_mgr.stock, "tags", None)
        if tag_service is None:
            raise RuntimeError("DataManager 未初始化 TagDataService: data_mgr.stock.tags 不存在")

        # 先校验 scenario 元信息是否存在；不存在则直接 fail-fast（比子进程刷 warning 更明确）
        scenario = tag_service.load_scenario(scenario_name)
        if not scenario:
            raise RuntimeError(
                "策略依赖的 Tag 场景不存在，已中断取数："
                f" stock_id={self.stock_id}, scenario={scenario_name}. "
                "请先运行 -t/-tg 生成标签元信息与数据，或检查 scenario 名称是否正确。"
            )

        data = tag_service.load_values_for_entity(
            entity_id=self.stock_id,
            scenario_name=scenario_name,
            start_date=start_date,
            end_date=end_date,
            # sys_tag_value.entity_type 在 tag 系统中通常存的是 target_entity.type（例如 stock_kline_daily），
            # 策略侧应使用一致的 entity_type 才能查到数据。
            entity_type=getattr(self.settings, "base_kline_type", "stock_kline_daily"),
        )
        return data or []
    
    def _load_finance_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """加载财务数据"""
        try:
            finance_model = self.data_mgr.get_table("sys_corporate_finance")
            if not finance_model:
                return []
            
            data = finance_model.load(
                condition="id = %s AND report_date >= %s AND report_date <= %s",
                params=(self.stock_id, start_date, end_date),
                order_by="report_date ASC"
            )
            return data if data else []

        except Exception as e:
            logger.error(f"加载财务数据失败: error={e}")
            return []
    
    def _load_macro_data(self, macro_type: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """加载宏观数据"""
        try:
            macro_model = self.data_mgr.get_table(macro_type)
            if not macro_model:
                return []
            
            data = macro_model.load(
                condition="date >= %s AND date <= %s",
                params=(start_date, end_date),
                order_by="date ASC"
            )
            return data if data else []

        except Exception as e:
            logger.error(f"加载宏观数据失败: type={macro_type}, error={e}")
            return []
    
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
    
    def _extract_term_from_kline_base(self, base_kline_type: str) -> str:
        """
        从 base_kline_type 提取周期
        
        Args:
            base_kline_type: 如 'stock_kline_daily' 或 EntityType.STOCK_KLINE_DAILY.value
        
        Returns:
            term: 'daily' or 'weekly' or 'monthly'
        """
        base_str = str(base_kline_type).lower()
        
        if 'daily' in base_str:
            return 'daily'
        elif 'weekly' in base_str:
            return 'weekly'
        elif 'monthly' in base_str:
            return 'monthly'
        
        # 默认返回 daily
        logger.warning(f"无法识别K线周期，使用默认值 daily: {base_kline_type}")
        return 'daily'
