#!/usr/bin/env python3
"""
Opportunity Enumerator Worker - 枚举器 Worker

职责：
- 在子进程中运行
- 枚举单个股票的所有投资机会
- 同时追踪多个 opportunities（可重叠）
- 每个 opportunity 独立 track 到完成
"""

from typing import Dict, Any, List
import logging
import time

from app.core.modules.strategy.components.opportunity_enumerator.performance_profiler import (
    PerformanceProfiler,
    PerformanceMetrics
)

logger = logging.getLogger(__name__)


class OpportunityEnumeratorWorker:
    """枚举器 Worker（子进程，带 DataManager / DB 访问）

    说明：
    - 这个 Worker 是最完整的版本，支持从 DB 加载历史数据、required_entities 等。
    - 在 DuckDB 单进程文件锁的前提下，我们仅在「单进程 / 单线程」模式下使用它。
    - 对于纯计算多进程场景，请使用 ComputeOnlyOpportunityEnumeratorWorker。
    """
    
    def __init__(self, job_payload: Dict[str, Any]):
        """
        初始化枚举器 Worker
        
        Args:
            job_payload: 作业负载，包含：
                - stock_id: 股票代码
                - strategy_name: 策略名称
                - settings: 策略配置字典
                - start_date: 开始日期
                - end_date: 结束日期
        """
        self.job_payload = job_payload
        
        # 提取基本信息
        self.stock_id = job_payload['stock_id']
        self.strategy_name = job_payload['strategy_name']
        self.start_date = job_payload['start_date']
        self.end_date = job_payload['end_date']
        
        # 初始化性能分析器（必须在最前面，以便记录整个生命周期）
        self.profiler = PerformanceProfiler(self.stock_id)
        
        # 解析配置
        from app.core.modules.strategy.models.strategy_settings import StrategySettings
        self.settings = StrategySettings.from_dict(job_payload['settings'])
        
        # 初始化数据管理器
        from app.core.modules.data_manager import DataManager
        self.data_mgr = DataManager(is_verbose=False)
        
        # 加载完整的股票信息（提前组织好，避免每次创建 Opportunity 时重复查询）
        self.stock_info = self._load_stock_info()
        
        from app.core.modules.strategy.components.strategy_worker_data_manager import StrategyWorkerDataManager
        self.data_manager = StrategyWorkerDataManager(
            stock_id=self.stock_id,
            settings=self.settings,
            data_mgr=self.data_mgr
        )
        
        # Opportunity ID 计数器（每个股票从 1 开始自增）
        self.opportunity_counter = 0
        
        # 动态导入用户策略
        self._load_user_strategy()
    
    def _load_stock_info(self) -> Dict[str, Any]:
        """
        加载股票信息（枚举器版本）
        
        说明：
        - 为了避免在多进程环境下对 stock_list 频繁 DB 访问导致
          MySQL 'Command Out of Sync' 错误，这里不再访问数据库，
          只返回最小必要字段。
        - 如果将来需要更丰富的元信息，可以在主进程预加载后通过 job_payload 传入。
        """
        return {
            "id": self.stock_id,
            "name": self.stock_id,
            "industry": "",
            "type": "",
            "exchange_center": "",
        }
    
    def _load_user_strategy(self):
        """动态加载用户策略"""
        import importlib
        import inspect
        from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
        
        module_path = f"app.userspace.strategies.{self.strategy_name}.strategy_worker"
        try:
            module = importlib.import_module(module_path)
            
            # 尝试多种类名查找方式
            strategy_class = None
            
            # 1. 尝试查找 'StrategyWorker'
            if hasattr(module, 'StrategyWorker'):
                strategy_class = getattr(module, 'StrategyWorker')
            # 2. 尝试查找 '{StrategyName}StrategyWorker'（首字母大写）
            else:
                strategy_name_capitalized = self.strategy_name.capitalize()
                class_name = f"{strategy_name_capitalized}StrategyWorker"
                if hasattr(module, class_name):
                    strategy_class = getattr(module, class_name)
            # 3. 如果还找不到，查找所有继承自 BaseStrategyWorker 的类
            if strategy_class is None:
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseStrategyWorker) and 
                        obj != BaseStrategyWorker):
                        strategy_class = obj
                        break
            
            if strategy_class is None:
                raise ValueError(f"找不到策略类: {module_path}")
            
            # 创建一个临时实例来获取 scan_opportunity 方法
            dummy_payload = {
                'stock_id': self.stock_id,
                'execution_mode': 'scan',
                'strategy_name': self.strategy_name,
                'settings': self.settings.to_dict()
            }
            self.strategy_instance = strategy_class(dummy_payload)
            
            # 将预加载的股票信息传递给策略实例（如果它需要）
            if hasattr(self.strategy_instance, 'stock_info'):
                self.strategy_instance.stock_info = self.stock_info
            
        except Exception as e:
            logger.error(f"加载策略失败: {self.strategy_name}, error={e}")
            raise
    
    def run(self) -> Dict[str, Any]:
        """
        运行枚举器（子进程入口）
        
        说明：
        - 枚举器（Layer 0）始终做“全量历史枚举”，当前 Worker 接收到的 start_date
          已经是全局 DEFAULT_START_DATE，由 OpportunityEnumerator 统一控制。
        - lookback 只影响“从哪一天开始对用户策略生效”（前面作为预热窗口），
          不影响加载的数据范围。
        
        Returns:
            {
                'success': True/False,
                'stock_id': '000001.SZ',
                'opportunity_count': int
            }
        """
        t_start = time.perf_counter()
        self.profiler.start_timer('total')
        try:
            # 1. 计算真正的开始日期（需要预留 lookback 窗口）
            # 使用 min_required_records 作为 lookback，但限制最大为 60 天。
            # 注意：这里仅用于“预热窗口”，不再用于截断历史。
            lookback_days = min(self.settings.min_required_records, 60)
            actual_start_date = self._get_date_before(self.start_date, lookback_days)
            
            # 2. 加载全量历史数据（支持批量预加载的 K 线）
            #
            # 说明：
            # - 如果 payload 中包含 `_preloaded_klines`，说明主进程已经按 batch
            #   一次性把这一批股票的 K 线查好了，这里直接复用，避免再次对 DB
            #   做「一股一查」。
            # - 否则，回退到原来的 per-stock `load_historical_data` 逻辑。
            import time as time_module
            self.profiler.start_timer('load_data')

            if '_preloaded_klines' in self.job_payload:
                # ===================== 预加载模式 =====================
                preloaded_klines = self.job_payload['_preloaded_klines']

                # 1) 注入 K 线数据
                self.data_manager._current_data['klines'] = preloaded_klines

                # 2) 计算技术指标（仅基于 K 线，一次性完成）
                self.data_manager._apply_indicators()

                # 3) 加载其他依赖数据（财务、Tag、宏观等，仍然按股票各查一次）
                required_entities_count = (
                    len(self.settings.required_entities)
                    if hasattr(self.settings, 'required_entities') else 0
                )

                if required_entities_count > 0:
                    entity_query_start = time_module.perf_counter()
                    for entity_config in self.settings.required_entities:
                        entity_type = (
                            entity_config.get('type')
                            if isinstance(entity_config, dict) else entity_config
                        )
                        data = self.data_manager._load_entity(
                            entity_config,
                            actual_start_date,
                            self.end_date,
                        )
                        self.data_manager._current_data[entity_type] = data
                    entity_query_time = time_module.perf_counter() - entity_query_start

                    # 这些查询仍然是 per-stock 的，这里按「每个实体一次查询」记账
                    avg_entity_query_time = (
                        entity_query_time / required_entities_count
                        if required_entities_count > 0 else 0
                    )
                    for _ in range(required_entities_count):
                        self.profiler.record_db_query(avg_entity_query_time)

                # 4) 初始化游标状态
                self.data_manager._init_cursor_state()

                self.profiler.metrics.time_load_data = self.profiler.end_timer('load_data')

                logger.debug(
                    "使用预加载K线数据: stock=%s, klines=%d",
                    self.stock_id,
                    len(preloaded_klines),
                )

            else:
                # ===================== 传统 per-stock 查询模式 =====================
                # 包装数据加载以统计 IO
                # 注意：load_historical_data 内部会执行数据库查询：
                # 1. load_qfq: 1 次查询（使用 JOIN 优化，一次查询出 K 线和复权因子）
                # 2. required_entities: 每个实体 1 次查询（如果有配置）
                db_query_start = time_module.perf_counter()
                self.data_manager.load_historical_data(
                    start_date=actual_start_date,
                    end_date=self.end_date
                )
                db_query_time = time_module.perf_counter() - db_query_start

                # 计算实际查询次数：1（K线 JOIN 查询）+ required_entities 数量
                required_entities_count = (
                    len(self.settings.required_entities)
                    if hasattr(self.settings, 'required_entities') else 0
                )
                estimated_queries = 1 + required_entities_count  # 1 次 K 线查询 + N 次实体查询
                avg_query_time = (
                    db_query_time / estimated_queries if estimated_queries > 0 else 0
                )
                for _ in range(estimated_queries):
                    self.profiler.record_db_query(avg_query_time)

                self.profiler.metrics.time_load_data = self.profiler.end_timer('load_data')
            
            # 3. 获取 K 线数据
            all_klines = self.data_manager.get_klines()
            
            if not all_klines:
                logger.warning(f"没有K线数据: stock={self.stock_id}")
                return {
                    'success': True,
                    'stock_id': self.stock_id,
                    'opportunity_count': 0,
                }
            
            # 3.1 数据质量检查：如果股票的总 K 线数 < min_required_records，跳过这个股票
            min_required_kline = self.settings.min_required_records
            if len(all_klines) < min_required_kline:
                logger.warning(
                    f"股票数据不足: stock={self.stock_id}, "
                    f"total_klines={len(all_klines)}, "
                    f"min_required={min_required_kline}"
                )
                return {
                    'success': True,
                    'stock_id': self.stock_id,
                    'opportunity_count': 0,
                }
            
            # 4. 初始化追踪器（⭐ 支持多投资）
            tracker = {
                'stock_id': self.stock_id,
                'passed_dates': [],
                'active_opportunities': [],  # ⭐ 改为列表
                'all_opportunities': []      # ⭐ 所有机会（包含已完成和未完成）
            }
            
            # 6. 逐日遍历 K 线
            self.profiler.start_timer('enumerate')
            last_kline = None
            for i, current_kline in enumerate(all_klines):
                virtual_date_of_today = current_kline['date']
                tracker['passed_dates'].append(virtual_date_of_today)
                
                # 如果未达到最小所需K线数，跳过
                if len(tracker['passed_dates']) < min_required_kline:
                    continue
                
                # 使用游标获取"今天及之前"的数据
                data_of_today = self.data_manager.get_data_until(virtual_date_of_today)
                
                # ⭐ 执行单日枚举（多投资）
                self._enumerate_single_day(tracker, current_kline, data_of_today)
                
                last_kline = current_kline
            self.profiler.metrics.time_enumerate = self.profiler.end_timer('enumerate')
            
            # 7. 回测结束，强制平仓所有未结投资
            if tracker['active_opportunities'] and last_kline:
                self._close_all_open_opportunities(tracker, last_kline)
            
            # 8. 序列化并写出本股票的 CSV，再返回精简 summary
            self.profiler.start_timer('serialize')
            opportunities_dict = [opp.to_dict() for opp in tracker['all_opportunities']]
            self.profiler.metrics.time_serialize = self.profiler.end_timer('serialize')

            opportunity_count = len(opportunities_dict)
            
            # 如果 payload 中有 output_dir，则将当前股票的结果写入对应目录
            output_dir = self.job_payload.get('output_dir')
            if output_dir and opportunity_count > 0:
                self.profiler.start_timer('save_csv')
                self._save_stock_results(output_dir, opportunities_dict)
                self.profiler.metrics.time_save_csv = self.profiler.end_timer('save_csv')
            
            # 更新数据统计
            self.profiler.metrics.kline_count = len(all_klines)
            self.profiler.metrics.opportunity_count = opportunity_count
            self.profiler.metrics.target_count = sum(
                len(opp.get('completed_targets', []) or []) 
                for opp in opportunities_dict
            )
            
            # 完成性能分析
            self.profiler.metrics.time_total = self.profiler.end_timer('total')
            metrics = self.profiler.finalize()

            logger.info(
                "⏱ 枚举性能[stock=%s]: load=%.1fms, enum=%.1fms, serialize=%.1fms, save=%.1fms, total=%.1fms, "
                "days=%d, opps=%d, db_queries=%d, file_writes=%d, memory_peak=%.1fMB",
                self.stock_id,
                metrics.time_load_data * 1000.0,
                metrics.time_enumerate * 1000.0,
                metrics.time_serialize * 1000.0,
                metrics.time_save_csv * 1000.0,
                metrics.time_total * 1000.0,
                len(all_klines),
                opportunity_count,
                metrics.db_queries,
                metrics.file_writes,
                metrics.memory_peak,
            )

            return {
                'success': True,
                'stock_id': self.stock_id,
                'opportunity_count': opportunity_count,
                'performance_metrics': metrics.to_dict(),  # 返回性能指标
            }
        
        except Exception as e:
            logger.error(
                f"枚举失败: stock_id={self.stock_id}, error={e}",
                exc_info=True
            )
            return {
                'success': False,
                'stock_id': self.stock_id,
                'opportunity_count': 0,
                'error': str(e)
            }


class ComputeOnlyOpportunityEnumeratorWorker:
    """
    纯计算版枚举 Worker（多进程安全）

    特点：
    - 不访问 DB，不依赖 DataManager/DatabaseManager
    - 只依赖 payload 中预加载的内存数据（klines + settings + output_dir）
    - 适合在「主进程已按 batch 从 DuckDB 拉好数据」的前提下进行多进程并行计算
    """

    def __init__(self, job_payload: Dict[str, Any]):
        """
        Args:
            job_payload: {
                'stock_id': str,
                'strategy_name': str,
                'settings': dict,           # StrategySettings dict
                'klines': List[Dict[str, Any]],
                'start_date': str,
                'end_date': str,
                'output_dir': str,
            }
        """
        self.job_payload = job_payload

        # 基本信息
        self.stock_id = job_payload['stock_id']
        self.strategy_name = job_payload['strategy_name']
        self.start_date = job_payload['start_date']
        self.end_date = job_payload['end_date']
        self.klines: List[Dict[str, Any]] = job_payload.get('klines') or []

        # 性能分析器
        self.profiler = PerformanceProfiler(self.stock_id)

        # 配置
        from app.core.modules.strategy.models.strategy_settings import StrategySettings
        self.settings = StrategySettings.from_dict(job_payload['settings'])

        # 股票元信息（最小字段集）
        self.stock_info = {
            "id": self.stock_id,
            "name": self.stock_id,
            "industry": "",
            "type": "",
            "exchange_center": "",
        }

        # Worker 级数据存储（仅内存，不访问 DB）
        self._current_data: Dict[str, Any] = {
            "klines": self.klines,
        }
        # 游标状态：与 StrategyWorkerDataManager 的设计一致
        self._cursor_state: Dict[str, Dict[str, Any]] = {}

        # Opportunity ID 计数器
        self.opportunity_counter = 0

        # 策略实例（延迟创建，避免触发 BaseStrategyWorker 的 DataManager 初始化）
        self.strategy_instance = None
        self._strategy_class = None
        self._strategy_module_path = f"app.userspace.strategies.{self.strategy_name}.strategy_worker"

    # -------- 策略与指标相关辅助 --------

    def _get_strategy_instance(self):
        """
        延迟创建策略实例（仅在需要时创建）
        
        注意：BaseStrategyWorker.__init__ 会初始化 DataManager，这在多进程环境下
        会导致 DuckDB 文件锁冲突。
        
        解决方案：创建一个最小包装器，直接调用策略类的 scan_opportunity 方法，
        而不通过 BaseStrategyWorker.__init__ 创建完整实例。
        """
        if self.strategy_instance is not None:
            return self.strategy_instance
        
        import importlib
        import inspect
        from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker

        try:
            if self._strategy_class is None:
                module = importlib.import_module(self._strategy_module_path)

                # 尝试多种类名查找方式
                strategy_class = None

                # 1. 尝试查找 'StrategyWorker'
                if hasattr(module, 'StrategyWorker'):
                    strategy_class = getattr(module, 'StrategyWorker')
                else:
                    # 2. 尝试查找 '{StrategyName}StrategyWorker'
                    strategy_name_capitalized = self.strategy_name.capitalize()
                    class_name = f"{strategy_name_capitalized}StrategyWorker"
                    if hasattr(module, class_name):
                        strategy_class = getattr(module, class_name)

                # 3. 如果还找不到，查找所有继承自 BaseStrategyWorker 的类
                if strategy_class is None:
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, BaseStrategyWorker)
                            and obj is not BaseStrategyWorker
                        ):
                            strategy_class = obj
                            break

                if strategy_class is None:
                    raise ValueError(f"找不到策略类: {self._strategy_module_path}")
                
                self._strategy_class = strategy_class

            # 创建最小包装器：不通过 BaseStrategyWorker.__init__，避免触发 DataManager 初始化
            # 使用 object.__new__ 创建实例，然后手动设置必要属性
            class ComputeOnlyStrategyWrapper:
                """最小策略包装器，避免触发 BaseStrategyWorker 的 DataManager 初始化"""
                def __init__(self, strategy_class, stock_info, stock_id, strategy_name, settings_dict):
                    # 直接创建实例，跳过 BaseStrategyWorker.__init__
                    # 这样不会触发 DataManager 初始化，避免 DuckDB 文件锁冲突
                    self._strategy_instance = object.__new__(strategy_class)
                    # 设置策略实例需要的最小属性（scan_opportunity 方法可能需要的）
                    self._strategy_instance.stock_info = stock_info
                    self._strategy_instance.stock_id = stock_id
                    self._strategy_instance.strategy_name = strategy_name
                    self._strategy_instance.job_payload = {
                        'stock_id': stock_id,
                        'strategy_name': strategy_name,
                        'settings': settings_dict,
                    }
                    # 注意：不设置 data_mgr 和 data_manager，因为 compute-only 模式下不需要
                    # 如果策略的 scan_opportunity 方法需要这些，说明策略设计有问题
                
                def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]):
                    """代理到真实策略实例的 scan_opportunity 方法"""
                    return self._strategy_instance.scan_opportunity(data, settings)
            
            # 创建包装器实例
            self.strategy_instance = ComputeOnlyStrategyWrapper(
                strategy_class=self._strategy_class,
                stock_info=self.stock_info,
                stock_id=self.stock_id,
                strategy_name=self.strategy_name,
                settings_dict=self.settings.to_dict(),
            )

        except Exception as e:
            logger.error(f"加载策略失败: {self.strategy_name}, error={e}")
            raise
        
        return self.strategy_instance

    def _apply_indicators(self) -> None:
        """
        根据 settings.data.indicators 使用 IndicatorService 计算指标，
        并将结果直接写回到 K 线字典中。
        """
        from app.core.modules.indicator import IndicatorService

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
                                field = self._build_indicator_field_name(
                                    f"{name}_{key}", cfg
                                )
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

    # -------- 游标机制（仅内存版） --------

    def _init_cursor_state(self):
        self._cursor_state = {}
        if "klines" in self._current_data:
            self._cursor_state["klines"] = {"cursor": -1, "acc": []}

    def _advance_cursor_until(
        self,
        data_list: List[Dict[str, Any]],
        state: Dict[str, Any],
        date_of_today: str,
        date_field: str = "date",
    ):
        cursor = state["cursor"]
        acc = state["acc"]

        i = cursor + 1
        n = len(data_list)

        while i < n:
            record = data_list[i]
            record_date = record.get(date_field)

            if not record_date or record_date > date_of_today:
                break

            acc.append(record)
            i += 1

        state["cursor"] = i - 1

    def get_data_until(self, date_of_today: str) -> Dict[str, Any]:
        """
        内存版游标：仅支持 klines
        """
        result: Dict[str, Any] = {}

        klines_state = self._cursor_state.get("klines")
        if klines_state:
            self._advance_cursor_until(
                data_list=self._current_data["klines"],
                state=klines_state,
                date_of_today=date_of_today,
                date_field="date",
            )
            result["klines"] = klines_state["acc"]

        return result

    # -------- 主执行逻辑（纯计算，多进程安全） --------

    def run(self) -> Dict[str, Any]:
        """
        入口：不触碰 DB，只使用 payload 中的内存数据
        """
        self.profiler.start_timer("total")
        try:
            # 1. 计算实际开始日期（只影响 lookback 逻辑）
            lookback_days = min(self.settings.min_required_records, 60)
            actual_start_date = self._get_date_before(self.start_date, lookback_days)

            # 2. load_data：应用指标 + 初始化游标
            import time as time_module

            self.profiler.start_timer("load_data")
            t0 = time_module.perf_counter()

            self._apply_indicators()
            self._init_cursor_state()

            _ = time_module.perf_counter() - t0  # 当前先不单独记录指标计算时间
            self.profiler.metrics.time_load_data = self.profiler.end_timer("load_data")

            all_klines = self._current_data.get("klines") or []
            if not all_klines:
                logger.warning("没有K线数据: stock=%s", self.stock_id)
                return {
                    "success": True,
                    "stock_id": self.stock_id,
                    "opportunity_count": 0,
                    "performance_metrics": self.profiler.finalize().to_dict(),
                }

            min_required_kline = self.settings.min_required_records
            if len(all_klines) < min_required_kline:
                logger.warning(
                    "股票数据不足: stock=%s, total_klines=%d, min_required=%d",
                    self.stock_id,
                    len(all_klines),
                    min_required_kline,
                )
                metrics = self.profiler.finalize()
                return {
                    "success": True,
                    "stock_id": self.stock_id,
                    "opportunity_count": 0,
                    "performance_metrics": metrics.to_dict(),
                }

            # 3. 逐日枚举
            tracker = {
                "stock_id": self.stock_id,
                "passed_dates": [],
                "active_opportunities": [],
                "all_opportunities": [],
            }

            self.profiler.start_timer("enumerate")
            last_kline = None
            for current_kline in all_klines:
                virtual_date_of_today = current_kline["date"]
                tracker["passed_dates"].append(virtual_date_of_today)

                if len(tracker["passed_dates"]) < min_required_kline:
                    continue

                data_of_today = self.get_data_until(virtual_date_of_today)
                self._enumerate_single_day(tracker, current_kline, data_of_today)
                last_kline = current_kline
            self.profiler.metrics.time_enumerate = self.profiler.end_timer("enumerate")

            # 4. 收尾：强制平仓所有未结机会
            if tracker["active_opportunities"] and last_kline:
                self._close_all_open_opportunities(tracker, last_kline)

            # 5. 序列化 + 写 CSV
            self.profiler.start_timer("serialize")
            opportunities_dict = [
                opp.to_dict() for opp in tracker["all_opportunities"]
            ]
            self.profiler.metrics.time_serialize = self.profiler.end_timer("serialize")

            opportunity_count = len(opportunities_dict)

            output_dir = self.job_payload.get("output_dir")
            if output_dir and opportunity_count > 0:
                self.profiler.start_timer("save_csv")
                self._save_stock_results(output_dir, opportunities_dict)
                self.profiler.metrics.time_save_csv = self.profiler.end_timer(
                    "save_csv"
                )

            self.profiler.metrics.kline_count = len(all_klines)
            self.profiler.metrics.opportunity_count = opportunity_count
            self.profiler.metrics.target_count = sum(
                len(opp.get("completed_targets", []) or [])
                for opp in opportunities_dict
            )

            self.profiler.metrics.time_total = self.profiler.end_timer("total")
            metrics = self.profiler.finalize()

            logger.info(
                "⏱[MP] 枚举性能[stock=%s]: load=%.1fms, enum=%.1fms, serialize=%.1fms, "
                "save=%.1fms, total=%.1fms, days=%d, opps=%d, file_writes=%d, memory_peak=%.1fMB",
                self.stock_id,
                metrics.time_load_data * 1000.0,
                metrics.time_enumerate * 1000.0,
                metrics.time_serialize * 1000.0,
                metrics.time_save_csv * 1000.0,
                metrics.time_total * 1000.0,
                len(all_klines),
                opportunity_count,
                metrics.file_writes,
                metrics.memory_peak,
            )

            return {
                "success": True,
                "stock_id": self.stock_id,
                "opportunity_count": opportunity_count,
                "performance_metrics": metrics.to_dict(),
            }

        except Exception as e:
            logger.error(
                "枚举失败(多进程计算): stock_id=%s, error=%s",
                self.stock_id,
                e,
                exc_info=True,
            )
            return {
                "success": False,
                "stock_id": self.stock_id,
                "opportunity_count": 0,
                "error": str(e),
            }
    
    def _enumerate_single_day(
        self,
        tracker: Dict[str, Any],
        current_kline: Dict[str, Any],
        data_of_today: Dict[str, Any]
    ):
        """
        枚举单日（⭐ 核心逻辑）
        
        流程：
        1. 检查所有 active opportunities 是否完成
        2. 扫描新机会（不管是否有持仓）
        
        Args:
            tracker: 追踪器
            current_kline: 当天的 K 线
            data_of_today: 今天及之前的所有数据
        """
        # 1. 检查所有 active opportunities
        completed_indices = []
        for idx, opportunity in enumerate(tracker['active_opportunities']):
            # ⭐ 使用 Opportunity 实例方法
            is_completed = opportunity.check_targets(
                current_kline=current_kline,
                goal_config=self.settings.goal
            )
            
            if is_completed:
                # 标记为已完成
                completed_indices.append(idx)
                
                logger.debug(
                    f"机会完成: stock={self.stock_id}, "
                    f"id={opportunity.opportunity_id}, "
                    f"date={current_kline['date']}, "
                    f"reason={opportunity.sell_reason}"
                )
        
        # 移除已完成的 opportunities（从后往前删除，避免索引错乱）
        for idx in reversed(completed_indices):
            tracker['active_opportunities'].pop(idx)
        
        # 2. 扫描新机会（⭐ 不管是否有持仓）
        opportunity = self._scan_opportunity_with_data(data_of_today)
        
        if opportunity:
            # 确保 stock 信息完整（使用 Worker 预加载的 stock_info）
            if opportunity.stock:
                opportunity.stock = {**self.stock_info, **opportunity.stock}
            else:
                opportunity.stock = self.stock_info
            
            # 设置买入信息
            opportunity.stock_id = self.stock_id
            opportunity.strategy_name = self.strategy_name
            opportunity.trigger_date = current_kline['date']
            opportunity.trigger_price = current_kline['close']
            opportunity.status = 'active'
            opportunity.completed_targets = []
            
            # 生成简单整数 ID（1, 2, 3, ...）
            self.opportunity_counter += 1
            opportunity.opportunity_id = str(self.opportunity_counter)
            
            # 框架自动填充其他字段（传入已设置的 opportunity_id）
            opportunity.enrich_from_framework(
                strategy_name=self.strategy_name,
                strategy_version='1.0',  # TODO: 从 settings 获取
                opportunity_id=opportunity.opportunity_id  # 已经设置，传入避免重复生成
            )
            
            # 加入追踪列表
            tracker['active_opportunities'].append(opportunity)
            tracker['all_opportunities'].append(opportunity)
            
            logger.debug(
                f"发现机会: stock={self.stock_id}, "
                f"id={opportunity.opportunity_id}, "
                f"date={opportunity.trigger_date}, "
                f"price={opportunity.trigger_price}"
            )
    
    def _scan_opportunity_with_data(self, data: Dict[str, Any]):
        """
        调用用户策略的 scan_opportunity 方法
        
        Args:
            data: 今天及之前的所有数据（包含 klines、required_entities 等）
        
        Returns:
            Opportunity or None
        """
        # 延迟创建策略实例（仅在第一次调用时）
        if self.strategy_instance is None:
            self._get_strategy_instance()
        
        # 直接调用用户实现的扫描方法，传入数据字典和配置
        settings_dict = self.settings.to_dict() if hasattr(self.settings, 'to_dict') else self.settings
        return self.strategy_instance.scan_opportunity(data, settings_dict)
    
    def _close_all_open_opportunities(self, tracker: Dict[str, Any], last_kline: Dict[str, Any]):
        """
        回测结束时强制平仓所有未结投资
        
        Args:
            tracker: 追踪器
            last_kline: 最后一个交易日的 K 线
        """
        for opportunity in tracker['active_opportunities']:
            # ⭐ 使用 Opportunity 实例方法
            opportunity.settle(
                last_kline=last_kline,
                reason='enumeration_end'
            )
            
            logger.debug(
                f"强制平仓: stock={self.stock_id}, "
                f"id={opportunity.opportunity_id}, "
                f"date={last_kline['date']}"
            )
        
        # 清空 active list（所有都已完成）
        tracker['active_opportunities'].clear()
    
    def _save_stock_results(self, output_dir: str, opportunities: List[Dict[str, Any]]):
        """
        将当前股票的机会和 completed_targets 写入单独的 CSV 文件：
        - {stock_id}_opportunities.csv
        - {stock_id}_targets.csv
        """
        from pathlib import Path
        import csv
        import json
        import time as time_module

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        total_write_size = 0

        opp_rows: List[Dict[str, Any]] = []
        target_rows: List[Dict[str, Any]] = []

        # 定义不需要输出到 CSV 的字段（内部追踪字段、元数据字段、原始数据字段、重复信息、空值字段）
        excluded_fields = {
            "completed_targets",  # 已单独输出到 targets CSV
            "config_hash",         # 策略配置 hash（版本控制用，CSV 不需要）
            "created_at",          # 创建时间（元数据，CSV 不需要）
            "updated_at",          # 更新时间（元数据，CSV 不需要）
            "record_of_today",     # 原始 K 线记录（已有 trigger_date/trigger_price，CSV 不需要）
            "dynamic_loss_active", # 动态止损激活状态（内部追踪，CSV 不需要）
            "dynamic_loss_highest", # 动态止损最高点（内部追踪，CSV 不需要）
            "expired_reason",      # 失效原因（如果机会过期，但当前设计不使用此字段）
            "expired_date",        # 失效日期（当前设计不使用，总是为空）
            "exit_reason",         # 退出原因（在 targets CSV 中已有 reason 字段，重复）
            "protect_loss_active", # 保本止损激活状态（内部追踪，CSV 不需要）
            # opportunity_id 保留在 CSV 中，用于关联 targets
            "scan_date",           # 扫描日期（元数据，CSV 不需要）
            "stock",               # 股票完整信息（已有 stock_id 和 stock_name，重复）
            "stock_id",            # 股票代码（文件名已表明，CSV 不需要）
            "stock_name",          # 股票名称（文件名已表明，CSV 不需要）
            "strategy_name",       # 策略名称（目录结构已表明，CSV 不需要）
            "strategy_version",    # 策略版本（元数据，CSV 不需要）
            "holding_days",        # 持有天数（当前实现中总是为空）
            "max_drawdown",        # 最大回撤（当前实现中总是为空）
            "metadata",            # 元数据（总是空字典）
            "price_return",        # 价格收益率（在 targets CSV 中已有 roi 字段，重复）
            "tracking",            # 持有期间追踪数据（当前实现中总是为空）
            "triggered_stop_loss_idx",    # 已触发的止损阶段索引（内部追踪状态，CSV 不需要）
            "triggered_take_profit_idx",  # 已触发的止盈阶段索引（内部追踪状态，CSV 不需要）
        }

        for opp in opportunities:
            # 主表数据（排除不需要的字段）
            row = {k: v for k, v in opp.items() if k not in excluded_fields}

            # 兼容旧字段名：sell_* -> exit_*
            if "sell_date" in row and "exit_date" not in row:
                row["exit_date"] = row.pop("sell_date")
            if "sell_price" in row and "exit_price" not in row:
                row["exit_price"] = row.pop("sell_price")
            if "sell_reason" in row and "exit_reason" not in row:
                row["exit_reason"] = row.pop("sell_reason")

            # price_return 和 roi 都已排除（在 targets CSV 中已有 roi 字段）

            # extra_fields 如果是 dict，则序列化为 JSON 字符串
            if "extra_fields" in row and isinstance(row["extra_fields"], dict):
                try:
                    row["extra_fields"] = json.dumps(row["extra_fields"], ensure_ascii=False)
                except Exception:
                    row["extra_fields"] = str(row["extra_fields"])

            opp_rows.append(row)

            # 子表数据（添加 opportunity_id 用于关联）
            opp_id = opp.get("opportunity_id")
            for target in opp.get("completed_targets", []) or []:
                t_row = dict(target)  # 直接使用 target 的字段
                # 添加 opportunity_id 用于关联
                if opp_id:
                    t_row["opportunity_id"] = opp_id
                if "extra_fields" in t_row and isinstance(t_row["extra_fields"], dict):
                    try:
                        t_row["extra_fields"] = json.dumps(t_row["extra_fields"], ensure_ascii=False)
                    except Exception:
                        t_row["extra_fields"] = str(t_row["extra_fields"])
                target_rows.append(t_row)

        # 写 opportunities CSV
        if opp_rows:
            opp_file = output_path / f"{self.stock_id}_opportunities.csv"
            fieldnames = sorted({k for row in opp_rows for k in row.keys()})
            t_write_start = time_module.perf_counter()
            with opp_file.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in opp_rows:
                    writer.writerow(row)
            write_size = opp_file.stat().st_size
            total_write_size += write_size
            write_time = time_module.perf_counter() - t_write_start
            self.profiler.record_file_write(write_size, write_time)

        # 写 targets CSV
        if target_rows:
            target_file = output_path / f"{self.stock_id}_targets.csv"
            fieldnames = sorted({k for row in target_rows for k in row.keys()})
            t_write_start = time_module.perf_counter()
            with target_file.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in target_rows:
                    writer.writerow(row)
            write_size = target_file.stat().st_size
            total_write_size += write_size
            write_time = time_module.perf_counter() - t_write_start
            self.profiler.record_file_write(write_size, write_time)
    
    def _get_date_before(self, date_str: str, days: int) -> str:
        """
        获取指定日期之前的日期
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            days: 天数
        
        Returns:
            更早的日期字符串（YYYYMMDD）
        """
        from datetime import datetime, timedelta
        
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            earlier_date = date - timedelta(days=days)
            return earlier_date.strftime('%Y%m%d')
        except Exception as e:
            logger.warning(f"计算日期失败: {e}")
            return date_str
