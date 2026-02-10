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

from core.modules.strategy.enums import ExecutionMode, OpportunityStatus
from core.modules.strategy.components.opportunity_enumerator.performance_profiler import (
    PerformanceProfiler,
    PerformanceMetrics
)

logger = logging.getLogger(__name__)

# 常量
MAX_LOOKBACK_DAYS = 60  # 最大历史窗口天数（用于数据加载）


class OpportunityEnumeratorWorker:
    """枚举器 Worker（子进程，带 DataManager / DB 访问）

    说明：
    - 这个 Worker 是最完整的版本，支持从 DB 加载历史数据、required_entities 等。
    - 在子进程中按需加载数据，通过 max_workers 限制并发数，避免内存爆炸。
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
        from core.modules.strategy.models.strategy_settings import StrategySettings
        self.settings = StrategySettings.from_dict(job_payload['settings'])
        
        # 初始化数据管理器
        from core.modules.data_manager import DataManager
        self.data_mgr = DataManager(is_verbose=False)
        
        # 加载完整的股票信息（提前组织好，避免每次创建 Opportunity 时重复查询）
        self.stock_info = self._load_stock_info()
        
        from core.modules.strategy.components.strategy_worker_data_manager import StrategyWorkerDataManager
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
        - 为了避免在多进程环境下对 stock_list 频繁 DB 访问，这里不再访问数据库，
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
        from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
        
        module_path = f"userspace.strategies.{self.strategy_name}.strategy_worker"
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
                'execution_mode': ExecutionMode.SCAN.value,
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
            # 使用 min_required_records 作为 lookback，但限制最大为 MAX_LOOKBACK_DAYS 天。
            # 注意：这里仅用于“预热窗口”，不再用于截断历史。
            lookback_days = min(self.settings.min_required_records, MAX_LOOKBACK_DAYS)
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
            opportunity.status = OpportunityStatus.ACTIVE.value
            opportunity.completed_targets = []
            
            # 生成简单整数 ID（1, 2, 3, ...）
            self.opportunity_counter += 1
            opportunity.opportunity_id = str(self.opportunity_counter)
            
            # 框架自动填充其他字段（传入已设置的 opportunity_id）
            opportunity.enrich_from_framework(
                strategy_name=self.strategy_name,
                strategy_version='1.0',  # 默认版本，后续可从 settings 获取
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
        }

        # 处理每个机会
        for opp in opportunities:
            # 转换为字典（如果已经是字典则直接使用）
            if hasattr(opp, 'to_dict'):
                opp_dict = opp.to_dict()
            elif isinstance(opp, dict):
                opp_dict = opp
            else:
                # 如果是 Opportunity 对象，手动转换
                opp_dict = {
                    'opportunity_id': getattr(opp, 'opportunity_id', ''),
                    'trigger_date': getattr(opp, 'trigger_date', ''),
                    'trigger_price': getattr(opp, 'trigger_price', 0.0),
                    'status': getattr(opp, 'status', ''),
                    'sell_reason': getattr(opp, 'sell_reason', ''),
                    'sell_date': getattr(opp, 'sell_date', ''),
                    'sell_price': getattr(opp, 'sell_price', 0.0),
                    'completed_targets': getattr(opp, 'completed_targets', []),
                }

            # 提取 completed_targets（单独输出到 targets CSV）
            completed_targets = opp_dict.get("completed_targets", [])
            if completed_targets:
                for target in completed_targets:
                    # 统一命名约定：
                    # - date / sell_price 表示实际成交（卖出）发生的日期和价格
                    # - sell_ratio / profit / weighted_profit / roi / reason 为本次成交属性
                    # 这里不再输出旧的 target_date / target_price 字段，避免和 sell_* 概念混淆。
                    target_row = {
                        "opportunity_id": opp_dict.get("opportunity_id", ""),
                        "date": target.get("date", ""),
                        "sell_price": target.get("price", ""),
                        "sell_ratio": target.get("sell_ratio", ""),
                        "profit": target.get("profit", ""),
                        "weighted_profit": target.get("weighted_profit", ""),
                        "reason": target.get("reason", ""),
                        "roi": target.get("roi", ""),
                    }
                    target_rows.append(target_row)

            # 过滤不需要的字段
            opp_row = {k: v for k, v in opp_dict.items() if k not in excluded_fields}
            
            # 处理特殊字段：将复杂对象转换为 JSON 字符串
            for key, value in opp_row.items():
                if isinstance(value, (dict, list)):
                    opp_row[key] = json.dumps(value, ensure_ascii=False)
                elif value is None:
                    opp_row[key] = ''

            opp_rows.append(opp_row)

        # 写入 opportunities CSV
        if opp_rows:
            from core.utils.io.csv_io import write_dicts_to_csv
            opp_file = output_path / f"{self.stock_id}_opportunities.csv"
            if opp_file.exists():
                opp_file.unlink()  # 删除旧文件

            # 使用第一行的 key 顺序作为首选顺序，保证列顺序稳定
            preferred_fields = list(opp_rows[0].keys())
            write_dicts_to_csv(opp_file, opp_rows, preferred_order=preferred_fields)
            total_write_size += opp_file.stat().st_size

        # 写入 targets CSV
        if target_rows:
            from core.utils.io.csv_io import write_dicts_to_csv
            target_file = output_path / f"{self.stock_id}_targets.csv"
            if target_file.exists():
                target_file.unlink()  # 删除旧文件

            preferred_fields = list(target_rows[0].keys())
            write_dicts_to_csv(target_file, target_rows, preferred_order=preferred_fields)
            total_write_size += target_file.stat().st_size

        logger.debug(
            f"已保存股票结果: stock={self.stock_id}, "
            f"opportunities={len(opp_rows)}, "
            f"targets={len(target_rows)}, "
            f"size={total_write_size / 1024:.2f}KB"
        )
