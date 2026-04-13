#!/usr/bin/env python3
"""
Base Strategy Worker - 策略 Worker 基类

职责：
- 在子进程中实例化（每个股票一个 Worker）
- 处理单个股票的扫描或回测
- 提供统一的生命周期接口
- 管理数据加载（通过 StrategyDataManager）

类比 BaseTagWorker
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

from core.modules.strategy.enums import ExecutionMode, OpportunityStatus
from core.modules.strategy.models.strategy_settings import StrategySettings
from core.modules.strategy.models.opportunity import Opportunity
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import DataKey
from core.modules.data_contract.data_contract_manager import DataContractManager

logger = logging.getLogger(__name__)

# 常量
MAX_LOOKBACK_DAYS = 60  # 最大历史窗口天数（用于数据加载）


class BaseStrategyWorker(ABC):
    """策略 Worker 基类（子进程）"""
    
    def __init__(self, job_payload: Dict[str, Any]):
        """
        初始化 Strategy Worker（只在子进程调用）
        
        Args:
            job_payload: 作业负载，包含：
                - stock_id: 股票代码
                - execution_mode: 'scan' or 'simulate'
                - strategy_name: 策略名称
                - settings: 策略配置字典
                - scan_date: 扫描日期（scan 模式）
                - opportunity: 机会字典（simulate 模式）
                - end_date: 结束日期（simulate 模式）
        """
        self.job_payload = job_payload
        
        # 提取基本信息
        self.stock_id = job_payload['stock_id']
        self.execution_mode = job_payload['execution_mode']  # ExecutionMode enum
        self.strategy_name = job_payload['strategy_name']
        
        # 解析配置
        self.settings = StrategySettings.from_dict(job_payload['settings'])
        
        self.contract_cache = ContractCacheManager()
        # 加载完整的股票信息（提前组织好，避免每次创建 Opportunity 时重复查询）
        self.stock_info = self._load_stock_info()
        from core.modules.strategy.components.data_management import StrategyDataManager
        self.data_manager = StrategyDataManager(
            stock_id=self.stock_id,
            settings=self.settings,
            contract_cache=self.contract_cache,
        )
        
        # Simulate 模式特有
        if self.execution_mode == ExecutionMode.SIMULATE.value:
            # 兼容两种 simulate job 结构：
            # 1) 旧版：按单个 opportunity 回放（payload 含 opportunity）
            # 2) 当前：按 stock 全历史逐日回测（payload 不含 opportunity）
            raw_opportunity = job_payload.get('opportunity')
            self.opportunity = (
                Opportunity.from_dict(raw_opportunity)
                if raw_opportunity else None
            )
            self.end_date = job_payload['end_date']
        else:
            self.scan_date = job_payload.get('scan_date')
        
        # 调用用户钩子
        self.on_init()
    
    # =========================================================================
    # 私有方法
    # =========================================================================
    
    def _load_stock_info(self) -> Dict[str, Any]:
        """
        加载完整的股票信息（子进程初始化时调用一次）
        
        Returns:
            Dict: 股票信息，包含 id, name, industry, type, exchange_center 等
        """
        try:
            dcm = DataContractManager(contract_cache=self.contract_cache)
            stock_list_contract = dcm.issue(DataKey.STOCK_LIST, filtered=False)
            stock_list = list(stock_list_contract.data or [])
            stock_info = next((x for x in stock_list if x.get("id") == self.stock_id), None)
            if isinstance(stock_info, dict):
                return stock_info
            
            # 如果都不可用，返回最小信息
            # 说明：
            # - 对于正常股票代码，这是一条有用的告警；
            # - 对于模拟钩子内部构造的 DUMMY 虚拟股票，则不需要在日志里打扰用户。
            if str(self.stock_id).upper() != "DUMMY":
                logger.warning(f"无法加载股票信息: {self.stock_id}，使用最小信息")
            return {
                'id': self.stock_id,
                'name': self.stock_id,
                'industry': '',
                'type': '',
                'exchange_center': ''
            }
        except Exception as e:
            if str(self.stock_id).upper() != "DUMMY":
                logger.error(f"加载股票信息失败: {self.stock_id}, error: {e}")
            return {
                'id': self.stock_id,
                'name': self.stock_id,
                'industry': '',
                'type': '',
                'exchange_center': ''
            }
    
    # =========================================================================
    # 生命周期方法（框架调用，用户不需要重写）
    # =========================================================================
    
    def run(self) -> Dict[str, Any]:
        """
        运行 Worker（子进程入口）
        
        这是 ProcessWorker 调用的统一入口
        
        Returns:
            result: {
                'success': True/False,
                'stock_id': '000001.SZ',
                'opportunity': {...} or None,
                'error': '...' (if failed)
            }
        """
        try:
            if self.execution_mode == ExecutionMode.SCAN.value:
                return self._execute_scan()
            elif self.execution_mode == ExecutionMode.SIMULATE.value:
                return self._execute_simulate()
            else:
                raise ValueError(f"未知的执行模式: {self.execution_mode}")
        
        except Exception as e:
            logger.error(
                f"处理股票失败: stock_id={self.stock_id}, "
                f"strategy={self.strategy_name}, "
                f"mode={self.execution_mode}, "
                f"error={e}",
                exc_info=True
            )
            return {
                'success': False,
                'stock_id': self.stock_id,
                'opportunity': None,
                'error': str(e)
            }
    
    def _execute_scan(self) -> Dict[str, Any]:
        """
        执行扫描模式
        
        流程：
        1. 加载最新数据（包含历史窗口，如 60 天）
        2. 调用用户实现的 scan_opportunity()
        3. 返回结果
        
        Returns:
            {
                'success': True,
                'stock_id': '000001.SZ',
                'opportunity': {...} or None
            }
        """
        # 1. 加载最新数据
        # 使用 min_required_records 作为 lookback，但限制最大为 MAX_LOOKBACK_DAYS 天
        lookback = min(self.settings.min_required_records, MAX_LOOKBACK_DAYS)
        self.data_manager.load_latest_data(lookback=lookback)
        
        # 2. 构建数据字典（格式与 get_data_until() 返回一致）
        data = self.data_manager.get_loaded_data()
        
        # 3. 调用用户钩子
        self.on_before_scan()
        
        # 4. 调用用户实现的扫描逻辑（传入数据字典和配置，避免 IO）
        opportunity = self.scan_opportunity(data, self.settings.to_dict())
        
        # 5. 如果用户返回了 Opportunity，确保 stock 信息完整（使用 Worker 预加载的 stock_info）
        if opportunity and opportunity.stock:
            # 合并预加载的完整股票信息（如果用户只提供了部分字段）
            opportunity.stock = {**self.stock_info, **opportunity.stock}
        
        # 5. 调用用户钩子
        self.on_after_scan(opportunity)
        
        # 5. 返回结果
        return {
            'success': True,
            'stock_id': self.stock_id,
            'opportunity': opportunity.to_dict() if opportunity else None
        }
    
    def _execute_simulate(self) -> Dict[str, Any]:
        """
        执行模拟模式（逐日回测）
        
        流程（避免上帝模式）：
        1. 加载全量历史数据（从更早的日期开始，确保有足够 lookback）
        2. 逐日遍历 K 线
        3. 每天使用游标过滤"今天及之前"的数据
        4. 调用用户的 scan_opportunity() 查找机会
        5. 追踪投资状态（止盈止损）
        6. 返回所有已完成的 opportunities
        
        Returns:
            {
                'success': True,
                'stock_id': '000001.SZ',
                'settled': [...]  # 所有已完成的 opportunities
            }
        """
        # 1. 计算真正的开始日期（需要预留 lookback 窗口）
        # 使用 min_required_records 作为 lookback，但限制最大为 MAX_LOOKBACK_DAYS 天
        lookback_days = min(self.settings.min_required_records, MAX_LOOKBACK_DAYS)
        
        # 从更早的日期开始加载，确保第一天就有足够的历史数据
        actual_start_date = self._get_date_before(
            self.job_payload.get('start_date'),  # simulate 的开始日期
            lookback_days
        )
        
        # 2. 加载全量历史数据
        self.data_manager.load_historical_data(
            start_date=actual_start_date,
            end_date=self.end_date
        )
        
        # 3. 获取 K 线数据
        all_klines = self.data_manager.get_klines()
        
        if not all_klines:
            logger.warning(f"没有K线数据: stock={self.stock_id}")
            return {
                'success': True,
                'stock_id': self.stock_id,
                'settled': []
            }
        
        # 4. 初始化追踪器
        tracker = {
            'stock_id': self.stock_id,
            'passed_dates': [],      # 已经过的日期
            'investing': None,        # 当前投资（Opportunity 对象）
            'settled': []            # 已完成的投资
        }
        
        # 5. 获取最小所需 K 线数
        min_required_kline = self.settings.min_required_records
        
        # 6. 逐日遍历 K 线（避免上帝模式）
        last_kline = None
        for i, current_kline in enumerate(all_klines):
            virtual_date_of_today = current_kline['date']
            tracker['passed_dates'].append(virtual_date_of_today)
            
            # 如果未达到最小所需K线数，跳过
            if len(tracker['passed_dates']) < min_required_kline:
                continue
            
            # 使用游标获取"今天及之前"的数据（避免上帝模式）
            data_of_today = self.data_manager.get_data_until(virtual_date_of_today)
            
            # 执行单日模拟
            self._execute_single_day(tracker, current_kline, data_of_today)
            
            last_kline = current_kline
        
        # 7. 回测结束，清算未结投资
        if tracker['investing'] and last_kline:
            self._settle_open_opportunity(tracker, last_kline)
        
        # 8. 清理临时数据
        del tracker['passed_dates']
        del tracker['investing']
        
        # 9. 返回结果
        return {
            'success': True,
            'stock_id': self.stock_id,
            'settled': tracker['settled']  # 所有已完成的 opportunities
        }
    
    def _execute_single_day(
        self, 
        tracker: Dict[str, Any], 
        current_kline: Dict[str, Any], 
        data_of_today: Dict[str, Any]
    ):
        """
        执行单日模拟
        
        流程：
        1. 如果有持仓，检查止盈止损
        2. 如果没持仓，调用用户的 scan_opportunity() 查找机会
        
        Args:
            tracker: 追踪器 {'investing': Opportunity or None, 'settled': [...]}
            current_kline: 当天的 K 线
            data_of_today: 今天及之前的所有数据（通过游标获取）
        """
        # 1. 检查现有投资
        if tracker['investing']:
            # ⭐ 使用 Opportunity 实例方法
            is_completed = tracker['investing'].check_targets(
                current_kline=current_kline,
                goal_config=self.settings.goal
            )
            
            if is_completed:
                # 投资完成，记录结果
                completed_opportunity = tracker['investing']
                tracker['settled'].append(tracker['investing'].to_dict())
                tracker['investing'] = None
                
                logger.debug(
                    f"投资完成: stock={self.stock_id}, "
                    f"date={current_kline['date']}, "
                    f"reason={completed_opportunity.sell_reason}"
                )
        
        # 2. 如果没有投资，扫描新机会
        if tracker['investing'] is None:
            # 调用用户实现的扫描方法
            opportunity = self.scan_opportunity_with_data(data_of_today)
            
            if opportunity:
                # 设置买入信息
                opportunity.trigger_date = current_kline['date']
                opportunity.trigger_price = current_kline['close']
                opportunity.status = OpportunityStatus.ACTIVE.value
                
                # 开始追踪这个投资
                tracker['investing'] = opportunity
                
                logger.debug(
                    f"发现机会: stock={self.stock_id}, "
                    f"date={current_kline['date']}, "
                    f"price={current_kline['close']}"
                )
    
    def _settle_open_opportunity(self, tracker: Dict[str, Any], last_kline: Dict[str, Any]):
        """
        回测结束时清算未结投资
        
        Args:
            tracker: 追踪器
            last_kline: 最后一个交易日的 K 线
        """
        opportunity = tracker.get('investing')
        if not opportunity:
            return
        
        # ⭐ 使用 Opportunity 实例方法
        opportunity.settle(
            last_kline=last_kline,
            reason='backtest_end'
        )
        
        # 记录到已完成列表
        tracker['settled'].append(opportunity.to_dict())
        tracker['investing'] = None
        
        logger.debug(
            f"清算未结投资: stock={self.stock_id}, "
            f"date={last_kline['date']}, "
            f"roi={opportunity.roi:.2%}"
        )
    
    def _get_date_before(self, date: str, days: int) -> str:
        """
        获取 N 天前的日期（使用 1.5 倍自然日，确保有足够的交易日数据）
        
        Args:
            date: 基准日期（YYYYMMDD）
            days: 天数（交易日数）
        
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
    
    def scan_opportunity_with_data(self, data: Dict[str, Any]) -> Optional['Opportunity']:
        """
        使用指定数据扫描机会（Simulator 内部调用）
        
        这是对用户 scan_opportunity() 的包装，直接传入数据字典和配置
        
        Args:
            data: 数据字典（通过游标过滤后的"今天及之前"的数据）
                包含：klines, tags, corporate_finance, macro 等
        
        Returns:
            Opportunity or None
        """
        # 直接调用用户实现的扫描方法，传入数据和配置
        return self.scan_opportunity(data, self.settings.to_dict())
    
    # =========================================================================
    # 抽象方法（用户必须实现）
    # =========================================================================
    
    @abstractmethod
    def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional['Opportunity']:
        """
        扫描投资机会（用户必须实现）
        
        框架提供：
        - self.stock_id: 当前股票代码
        - data: 数据字典（通过游标过滤后的"今天及之前"的数据）
            - data['klines']: List[Dict] - K线数据（已包含技术指标）
            - data.get('tags', []): List[Dict] - 标签数据（如果配置了 required_entities）
            - data.get('corporate_finance', []): List[Dict] - 财务数据（如果配置了）
            - data.get('macro', {}): Dict - 宏观数据（如果配置了）
        - settings: 策略配置字典（包含 core、data、simulator、goal 等）
        
        重要：
        - 数据通过参数传入，避免每次调用触发 IO
        - 直接从 data 字典中获取数据，不要通过 self.data_manager.get_klines()
        - 配置通过 settings 参数传入，不要使用 self.settings
        
        用户需要：
        1. 从 data 参数中获取数据：klines = data.get('klines', [])
        2. 从 settings 参数中获取配置：rsi_threshold = settings.get('core', {}).get('rsi_oversold_threshold', 35)
        3. 分析最新数据
        4. 判断是否有买入信号
        5. 如果有，创建并返回 Opportunity 对象
        6. 如果没有，返回 None
        
        Args:
            data: 数据字典，包含 klines、required_entities 等
            settings: 策略配置字典
        
        Returns:
            Opportunity: 投资机会（如果发现）
            None: 没有发现机会
        
        示例：
            klines = data.get('klines', [])
            if len(klines) < 60:
                return None
            
            # 获取配置
            rsi_threshold = settings.get('core', {}).get('rsi_oversold_threshold', 35)
            
            # 获取最新 K 线
            latest_kline = klines[-1]
            
            # 判断条件
            if klines[-1]['close'] > ma20:
                return Opportunity(
                    # opportunity_id 会在 enrich_from_framework 中自动生成
                    stock_id=self.stock_id,
                    trigger_date=klines[-1]['date'],
                    trigger_price=klines[-1]['close'],
                    ...
                )
            
            return None
        """
        pass
    
    # =========================================================================
    # 钩子方法（用户可选重写）
    # =========================================================================
    
    # ---- 枚举 / 回测通用钩子 -------------------------------------------------
    
    def on_init(self):
        """初始化钩子（可选重写）"""
        pass
    
    def on_before_scan(self):
        """扫描前钩子（可选重写）"""
        pass
    
    def on_after_scan(self, opportunity: Optional['Opportunity']):
        """扫描后钩子（可选重写）"""
        pass
    
    def on_before_simulate(self, opportunity: 'Opportunity'):
        """模拟前钩子（可选重写）"""
        pass
    
    def on_after_simulate(self, opportunity: 'Opportunity'):
        """模拟后钩子（可选重写）"""
        pass
    
    # ---- PriceFactorSimulator 相关钩子 --------------------------------------
    
    def on_price_factor_before_process_stock(
        self,
        stock_id: str,
        opportunities: 'list[dict]',
        config: 'dict',
    ) -> None:
        """
        价格因子模拟：处理单只股票前钩子（可选重写）
        
        Args:
            stock_id: 股票代码
            opportunities: 该股的机会原始记录列表（CSV 行字典）
            config: PriceFactorSimulatorConfig 的字典视图
        """
        return None
    
    def on_price_factor_after_process_stock(
        self,
        stock_id: str,
        stock_summary: 'dict',
        config: 'dict',
    ) -> 'dict':
        """
        价格因子模拟：处理单只股票后钩子（可选重写，可修改汇总结果）
        
        Args:
            stock_id: 股票代码
            stock_summary: {
                "stock": {...},
                "investments": [...],
                "summary": {...},
            }
            config: PriceFactorSimulatorConfig 的字典视图
        
        Returns:
            修改后的 stock_summary 字典；默认返回原样
        """
        return stock_summary
    
    def on_price_factor_opportunity_trigger(
        self,
        opportunity_row: 'dict',
        config: 'dict',
    ) -> 'dict':
        """
        价格因子模拟：机会触发时钩子（可选重写，可修改机会数据）
        
        Args:
            opportunity_row: 来自 opportunities.csv 的单行记录
            config: PriceFactorSimulatorConfig 的字典视图
        
        Returns:
            修改后的机会字典；默认返回原样
        """
        return opportunity_row
    
    def on_price_factor_target_hit(
        self,
        target_row: 'dict',
        opportunity_row: 'dict',
        config: 'dict',
    ) -> 'dict':
        """
        价格因子模拟：目标命中时钩子（可选重写，可修改目标数据）
        
        Args:
            target_row: 来自 targets.csv 的单行记录
            opportunity_row: 对应的机会记录
            config: PriceFactorSimulatorConfig 的字典视图
        
        Returns:
            修改后的目标字典；默认返回原样
        """
        return target_row
    
    # ---- CapitalAllocationSimulator 相关钩子 --------------------------------
    
    def on_capital_allocation_before_trigger_event(
        self,
        event: 'Any',
        account: 'Any',
        config: 'Any',
    ):
        """
        资金分配模拟：触发事件处理前钩子（可选重写，可修改事件）
        
        Args:
            event: Event 实例
            account: Account 实例
            config: CapitalAllocationSimulatorConfig 实例
        
        Returns:
            修改后的 event；默认返回原样
        """
        return event
    
    def on_capital_allocation_after_trigger_event(
        self,
        event: 'Any',
        trade: 'dict',
        account: 'Any',
        config: 'Any',
    ):
        """
        资金分配模拟：触发事件处理后钩子（可选重写，可修改交易记录）
        
        Args:
            event: Event 实例
            trade: 本次买入生成的交易字典
            account: Account 实例
            config: CapitalAllocationSimulatorConfig 实例
        
        Returns:
            修改后的 trade 字典；默认返回原样
        """
        return trade
    
    def on_capital_allocation_before_target_event(
        self,
        event: 'Any',
        account: 'Any',
        config: 'Any',
    ):
        """
        资金分配模拟：目标事件处理前钩子（可选重写，可修改事件）
        """
        return event
    
    def on_capital_allocation_after_target_event(
        self,
        event: 'Any',
        trade: 'dict',
        account: 'Any',
        config: 'Any',
    ):
        """
        资金分配模拟：目标事件处理后钩子（可选重写，可修改交易记录）
        """
        return trade
    
    def on_capital_allocation_calculate_shares_to_buy(
        self,
        event: 'Any',
        account: 'Any',
        config: 'Any',
        default_shares: int,
    ):
        """
        资金分配模拟：计算买入股数钩子（可选重写，可自定义分配逻辑）
        
        Args:
            event: 触发事件
            account: Account 实例
            config: CapitalAllocationSimulatorConfig 实例
            default_shares: 默认计算出的买入股数
        
        Returns:
            int: 自定义买入股数；返回 None 表示使用默认值
        """
        return None
    
    def on_capital_allocation_calculate_shares_to_sell(
        self,
        event: 'Any',
        position: 'Any',
        config: 'Any',
        default_shares: int,
    ):
        """
        资金分配模拟：计算卖出股数钩子（可选重写，可自定义卖出逻辑）
        
        Args:
            event: 目标事件
            position: Position 实例
            config: CapitalAllocationSimulatorConfig 实例
            default_shares: 默认计算出的卖出股数
        
        Returns:
            int: 自定义卖出股数；返回 None 表示使用默认值
        """
        return None
