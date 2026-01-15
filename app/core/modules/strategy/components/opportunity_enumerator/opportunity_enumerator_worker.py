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

logger = logging.getLogger(__name__)


class OpportunityEnumeratorWorker:
    """枚举器 Worker（子进程）"""
    
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
                - mode: 'simplified' or 'full'
                - signal_window: 信号窗口（simplified 模式）
        """
        self.job_payload = job_payload
        
        # 提取基本信息
        self.stock_id = job_payload['stock_id']
        self.strategy_name = job_payload['strategy_name']
        self.start_date = job_payload['start_date']
        self.end_date = job_payload['end_date']
        self.mode = job_payload.get('mode', 'simplified')
        self.signal_window = job_payload.get('signal_window', 3)
        
        # 解析配置
        from app.core.modules.strategy.models.strategy_settings import StrategySettings
        self.settings = StrategySettings.from_dict(job_payload['settings'])
        
        # 初始化数据管理器
        from app.core.modules.data_manager import DataManager
        self.data_mgr = DataManager(is_verbose=False)
        
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
    
    def _load_user_strategy(self):
        """动态加载用户策略"""
        import importlib
        
        module_path = f"app.userspace.strategies.{self.strategy_name}.strategy_worker"
        try:
            module = importlib.import_module(module_path)
            strategy_class = getattr(module, 'StrategyWorker')
            
            # 创建一个临时实例来获取 scan_opportunity 方法
            # 注意：这里我们需要传入一个虚拟的 job_payload
            dummy_payload = {
                'stock_id': self.stock_id,
                'execution_mode': 'scan',
                'strategy_name': self.strategy_name,
                'settings': self.settings.to_dict()
            }
            self.strategy_instance = strategy_class(dummy_payload)
            
        except Exception as e:
            logger.error(f"加载策略失败: {self.strategy_name}, error={e}")
            raise
    
    def run(self) -> Dict[str, Any]:
        """
        运行枚举器（子进程入口）
        
        Returns:
            {
                'success': True/False,
                'stock_id': '000001.SZ',
                'opportunities': [...]  # 所有机会（包含 completed 和 open）
            }
        """
        try:
            # 1. 计算真正的开始日期（需要预留 lookback 窗口）
            # 使用 min_required_records 作为 lookback，但限制最大为 60 天
            lookback_days = min(self.settings.min_required_records, 60)
            actual_start_date = self._get_date_before(self.start_date, lookback_days)
            
            # 2. 加载全量历史数据（优先使用预加载的数据）
            import time as time_module
            
            # 初始化 profiler 计时
            self.profiler.start_timer('load_data')
            
            if '_preloaded_klines' in self.job_payload:
                # 使用预加载的K线数据（批量查询优化）
                # 注意：K线数据已经在主进程批量查询完成，这里不再记录为 db_query
                preloaded_klines = self.job_payload['_preloaded_klines']
                self.data_manager._current_data['klines'] = preloaded_klines
                
                # 计算技术指标（基于预加载的K线）
                self.data_manager._apply_indicators()
                
                # 加载其他依赖数据（财务、tag等，仍然按股票查询）
                # 这些查询需要单独记录
                required_entities_count = len(self.settings.required_entities) if hasattr(self.settings, 'required_entities') else 0
                
                if required_entities_count > 0:
                    # 记录其他实体的查询时间
                    entity_query_start = time_module.perf_counter()
                    for entity_config in self.settings.required_entities:
                        entity_type = entity_config.get('type') if isinstance(entity_config, dict) else entity_config
                        data = self.data_manager._load_entity(entity_config, actual_start_date, self.end_date)
                        self.data_manager._current_data[entity_type] = data
                    entity_query_time = time_module.perf_counter() - entity_query_start
                    
                    # 记录其他实体的查询（每个实体 1 次查询）
                    avg_entity_query_time = entity_query_time / required_entities_count if required_entities_count > 0 else 0
                    for _ in range(required_entities_count):
                        self.profiler.record_db_query(avg_entity_query_time)
                else:
                    # 没有其他实体，不记录任何 db_query（K线已批量查询）
                    pass
                
                # 初始化游标状态
                self.data_manager._init_cursor_state()
                
                logger.debug(f"使用预加载数据: stock={self.stock_id}, klines={len(preloaded_klines)}")
            else:
                # 回退到原来的单股票查询方式
                db_query_start = time_module.perf_counter()
                self.data_manager.load_historical_data(
                    start_date=actual_start_date,
                    end_date=self.end_date
                )
                db_query_time = time_module.perf_counter() - db_query_start
                
                # 计算实际查询次数：1（K线 JOIN 查询）+ required_entities 数量
                required_entities_count = len(self.settings.required_entities) if hasattr(self.settings, 'required_entities') else 0
                estimated_queries = 1 + required_entities_count  # 1 次 K 线查询 + N 次实体查询
                avg_query_time = db_query_time / estimated_queries if estimated_queries > 0 else 0
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
                    'opportunities': []
                }
            
            # 4. 初始化追踪器（⭐ 支持多投资）
            tracker = {
                'stock_id': self.stock_id,
                'passed_dates': [],
                'active_opportunities': [],  # ⭐ 改为列表
                'all_opportunities': []      # ⭐ 所有机会（包含已完成和未完成）
            }
            
            # 5. 获取最小所需 K 线数
            min_required_kline = self.settings.min_required_records
            
            # 6. 逐日遍历 K 线
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
            
            # 7. 回测结束，强制平仓所有未结投资
            if tracker['active_opportunities'] and last_kline:
                self._close_all_open_opportunities(tracker, last_kline)
            
            # 8. 序列化并返回结果
            opportunities_dict = [
                opp.to_dict() for opp in tracker['all_opportunities']
            ]
            
            return {
                'success': True,
                'stock_id': self.stock_id,
                'opportunities': opportunities_dict
            }
        
        except Exception as e:
            logger.error(
                f"枚举失败: stock_id={self.stock_id}, error={e}",
                exc_info=True
            )
            return {
                'success': False,
                'stock_id': self.stock_id,
                'opportunities': [],
                'error': str(e)
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
            from app.core.modules.strategy.models.opportunity import Opportunity
            
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
            
            # 加入追踪列表
            tracker['active_opportunities'].append(opportunity)
            tracker['all_opportunities'].append(opportunity)
            
            logger.debug(
                f"发现机会: stock={self.stock_id}, "
                f"id={opportunity.opportunity_id}, "
                f"date={current_kline['date']}, "
                f"price={current_kline['close']}"
            )
    
    def _scan_opportunity_with_data(self, data: Dict[str, Any]):
        """
        调用用户策略的 scan_opportunity 方法
        
        Args:
            data: 今天及之前的所有数据
        
        Returns:
            Opportunity or None
        """
        # 临时设置数据（模拟 BaseStrategyWorker 的行为）
        self.strategy_instance.data_manager._current_data = data
        
        # 调用用户实现的扫描方法
        opportunity = self.strategy_instance.scan_opportunity()
        
        return opportunity
    
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
