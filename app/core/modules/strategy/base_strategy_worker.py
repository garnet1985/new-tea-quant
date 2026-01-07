#!/usr/bin/env python3
"""
Base Strategy Worker - 策略 Worker 基类

职责：
- 在子进程中实例化（每个股票一个 Worker）
- 处理单个股票的扫描或回测
- 提供统一的生命周期接口
- 管理数据加载（通过 StrategyWorkerDataManager）

类比 BaseTagWorker
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


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
        from app.core.modules.strategy.models.strategy_settings import StrategySettings
        from app.core.modules.strategy.enums import ExecutionMode
        
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
        
        # Simulate 模式特有
        if self.execution_mode == ExecutionMode.SIMULATE.value:
            from app.core.modules.strategy.models.opportunity import Opportunity
            self.opportunity = Opportunity.from_dict(job_payload['opportunity'])
            self.end_date = job_payload['end_date']
        else:
            self.scan_date = job_payload.get('scan_date')
        
        # 调用用户钩子
        self.on_init()
    
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
        from app.core.modules.strategy.enums import ExecutionMode
        
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
        lookback = self.settings.params.get('lookback_days', 60)
        self.data_manager.load_latest_data(lookback=lookback)
        
        # 2. 调用用户钩子
        self.on_before_scan()
        
        # 3. 调用用户实现的扫描逻辑
        opportunity = self.scan_opportunity()
        
        # 4. 调用用户钩子
        self.on_after_scan(opportunity)
        
        # 5. 返回结果
        return {
            'success': True,
            'stock_id': self.stock_id,
            'opportunity': opportunity.to_dict() if opportunity else None
        }
    
    def _execute_simulate(self) -> Dict[str, Any]:
        """
        执行模拟模式（框架自动实现回测逻辑）
        
        流程：
        1. 加载历史数据（从 trigger_date 到 end_date）
        2. 根据 goal 配置自动执行回测
        3. 返回更新后的 Opportunity
        
        Returns:
            {
                'success': True,
                'stock_id': '000001.SZ',
                'opportunity': {...}  # 更新后的 Opportunity
            }
        """
        # 1. 加载历史数据
        self.data_manager.load_historical_data(
            start_date=self.opportunity.trigger_date,
            end_date=self.end_date
        )
        
        # 2. 调用用户钩子
        self.on_before_simulate(self.opportunity)
        
        # 3. 框架自动执行回测（根据 goal 配置）
        updated_opportunity = self._auto_simulate_opportunity(self.opportunity)
        
        # 4. 调用用户钩子
        self.on_after_simulate(updated_opportunity)
        
        # 5. 返回结果
        return {
            'success': True,
            'stock_id': self.stock_id,
            'opportunity': updated_opportunity.to_dict()
        }
    
    def _auto_simulate_opportunity(self, opportunity: 'Opportunity') -> 'Opportunity':
        """
        框架自动执行回测（根据 goal 配置）
        
        用户不需要实现此方法，框架根据 settings.goal 自动执行：
        - 止盈止损
        - 分段止盈止损
        - 动态止损
        - 保本止损
        - 到期平仓
        
        Args:
            opportunity: 要回测的机会
        
        Returns:
            Opportunity: 更新后的机会
        """
        # 获取 K线 数据
        klines = self.data_manager.get_klines()
        
        # 找到买入日期的索引
        buy_index = None
        for i, k in enumerate(klines):
            if k['date'] == opportunity.trigger_date:
                buy_index = i
                break
        
        if buy_index is None:
            opportunity.status = 'expired'
            opportunity.expired_reason = 'trigger_date_not_found'
            return opportunity
        
        buy_price = opportunity.trigger_price
        goal_config = self.settings.goal
        
        # 初始化追踪变量
        sell_date = None
        sell_price = None
        sell_reason = None
        max_price = buy_price
        min_price = buy_price
        tracking_prices = []
        tracking_returns = []
        
        # 止盈止损状态追踪
        stop_loss_stages = goal_config.get('stop_loss', {}).get('stages', [])
        take_profit_stages = goal_config.get('take_profit', {}).get('stages', [])
        expiration_config = goal_config.get('expiration', {})
        
        # 已触发的阶段索引
        triggered_stop_loss_idx = -1
        triggered_take_profit_idx = -1
        
        # 动态止损相关
        protect_loss_active = False
        dynamic_loss_active = False
        dynamic_loss_highest = buy_price
        
        # 遍历持有期
        for i in range(buy_index + 1, len(klines)):
            current_kline = klines[i]
            current_price = current_kline['close']
            holding_days = i - buy_index
            
            # 记录追踪数据
            tracking_prices.append(current_price)
            price_return = (current_price - buy_price) / buy_price
            tracking_returns.append(price_return)
            
            # 更新最高最低价
            max_price = max(max_price, current_price)
            min_price = min(min_price, current_price)
            
            # 更新动态止损最高点
            if dynamic_loss_active:
                dynamic_loss_highest = max(dynamic_loss_highest, current_price)
            
            # 1. 检查到期平仓
            if expiration_config:
                fixed_period = expiration_config.get('fixed_period', 0)
                is_trading_period = expiration_config.get('is_trading_period', True)
                
                if is_trading_period and holding_days >= fixed_period:
                    sell_date = current_kline['date']
                    sell_price = current_price
                    sell_reason = 'expiration'
                    break
            
            # 2. 检查保本止损
            if protect_loss_active:
                protect_loss_config = goal_config.get('protect_loss', {})
                protect_ratio = protect_loss_config.get('ratio', 0)
                
                if price_return <= protect_ratio:
                    sell_date = current_kline['date']
                    sell_price = current_price
                    sell_reason = 'protect_loss'
                    break
            
            # 3. 检查动态止损
            if dynamic_loss_active:
                dynamic_loss_config = goal_config.get('dynamic_loss', {})
                dynamic_ratio = dynamic_loss_config.get('ratio', -0.1)
                dynamic_threshold = (current_price - dynamic_loss_highest) / dynamic_loss_highest
                
                if dynamic_threshold <= dynamic_ratio:
                    sell_date = current_kline['date']
                    sell_price = current_price
                    sell_reason = 'dynamic_loss'
                    break
            
            # 4. 检查分段止损
            for idx, stage in enumerate(stop_loss_stages):
                if idx <= triggered_stop_loss_idx:
                    continue
                
                stage_ratio = stage.get('ratio', 0)
                if price_return <= stage_ratio:
                    # 触发止损
                    triggered_stop_loss_idx = idx
                    
                    # 判断是否清仓
                    if stage.get('close_invest', False):
                        sell_date = current_kline['date']
                        sell_price = current_price
                        sell_reason = f"stop_loss_{stage.get('name', idx)}"
                        break
            
            if sell_date:
                break
            
            # 5. 检查分段止盈
            for idx, stage in enumerate(take_profit_stages):
                if idx <= triggered_take_profit_idx:
                    continue
                
                stage_ratio = stage.get('ratio', 0)
                if price_return >= stage_ratio:
                    # 触发止盈
                    triggered_take_profit_idx = idx
                    
                    # 执行动作
                    actions = stage.get('actions', [])
                    if 'set_protect_loss' in actions:
                        protect_loss_active = True
                    if 'set_dynamic_loss' in actions:
                        dynamic_loss_active = True
                        dynamic_loss_highest = current_price
                    
                    # 判断是否清仓
                    if stage.get('close_invest', False):
                        sell_date = current_kline['date']
                        sell_price = current_price
                        sell_reason = f"take_profit_{stage.get('name', idx)}"
                        break
            
            if sell_date:
                break
        
        # 如果没有触发卖出，最后一天卖出
        if not sell_date:
            sell_date = klines[-1]['date']
            sell_price = klines[-1]['close']
            sell_reason = 'end_of_period'
        
        # 更新 Opportunity
        opportunity.sell_date = sell_date
        opportunity.sell_price = sell_price
        opportunity.sell_reason = sell_reason
        opportunity.price_return = (sell_price - buy_price) / buy_price
        opportunity.holding_days = len(tracking_prices)
        opportunity.max_price = max_price
        opportunity.min_price = min_price
        opportunity.max_drawdown = (min_price - buy_price) / buy_price
        opportunity.tracking = {
            'daily_prices': tracking_prices,
            'daily_returns': tracking_returns
        }
        opportunity.status = 'closed'
        opportunity.updated_at = datetime.now().isoformat()
        
        return opportunity
    
    # =========================================================================
    # 抽象方法（用户必须实现）
    # =========================================================================
    
    @abstractmethod
    def scan_opportunity(self) -> Optional['Opportunity']:
        """
        扫描投资机会（用户必须实现）
        
        框架提供：
        - self.stock_id: 当前股票代码
        - self.data_manager: 数据管理器
            - self.data_manager.get_klines() -> List[Dict]
            - self.data_manager.get_entity_data(type) -> List[Dict]
        - self.settings: 策略配置
        
        用户需要：
        1. 获取数据：klines = self.data_manager.get_klines()
        2. 分析最新数据
        3. 判断是否有买入信号
        4. 如果有，创建并返回 Opportunity 对象
        5. 如果没有，返回 None
        
        Returns:
            Opportunity: 投资机会（如果发现）
            None: 没有发现机会
        
        示例：
            klines = self.data_manager.get_klines()
            if len(klines) < 60:
                return None
            
            # 计算指标
            ma20 = sum(k['close'] for k in klines[-20:]) / 20
            
            # 判断条件
            if klines[-1]['close'] > ma20:
                return Opportunity(
                    opportunity_id=str(uuid.uuid4()),
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
