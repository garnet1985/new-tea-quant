"""
投资目标计算器 - 计算下一止损和下一止盈目标
"""
from typing import Dict, Any, List, Optional
import logging
import json
import importlib


logger = logging.getLogger(__name__)


class TargetCalculator:
    """投资目标计算器"""
    
    @staticmethod
    def calculate_next_targets(
        holding: Dict[str, Any],
        current_price: float,
        goal_config: Optional[str],
        operations: List[Dict[str, Any]],
        strategy_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算下一个止损和止盈目标
        
        Args:
            holding: 当前持仓信息 {amount, avg_cost, ...}
            current_price: 当前价格
            goal_config: 策略goal配置（JSON字符串）
            operations: 所有操作记录（包含卖出历史）
            
        Returns:
            Dict: {
                'next_stop_loss': None or {name, type, ratio, target_price, ...},
                'next_take_profit': None or {name, type, ratio, target_price, ...},
                'completed_stop_losses': [],  # 已达成的止损
                'completed_take_profits': [],  # 已达成的止盈
                'is_customized': False,  # 是否为customized策略
            }
        """
        if not goal_config:
            return {
                'next_stop_loss': None,
                'next_take_profit': None,
                'completed_stop_losses': [],
                'completed_take_profits': [],
                'is_customized': False
            }
        
        try:
            goal = json.loads(goal_config) if isinstance(goal_config, str) else goal_config
        except Exception as e:
            logger.error(f"解析goal_config失败: {e}")
            return {
                'next_stop_loss': None,
                'next_take_profit': None,
                'completed_stop_losses': [],
                'completed_take_profits': [],
                'is_customized': False
            }
        
        avg_cost = holding.get('avg_cost', 0)
        amount = holding.get('amount', 0)
        
        if not avg_cost or not amount:
            return {
                'next_stop_loss': None,
                'next_take_profit': None,
                'completed_stop_losses': [],
                'completed_take_profits': [],
                'is_customized': False
            }
        
        stop_loss_config = goal.get('stop_loss', {})
        take_profit_config = goal.get('take_profit', {})
        
        # 检查是否是customized策略
        is_customized_sl = stop_loss_config.get('is_customized', False)
        is_customized_tp = take_profit_config.get('is_customized', False)
        is_customized = is_customized_sl or is_customized_tp
        
        if is_customized:
            # 对于customized策略，通过should_stop_loss/should_take_profit获取目标
            next_stop_loss = None
            next_take_profit = None
            
            if strategy_name:
                try:
                    # 加载策略
                    from core.infra.db import DatabaseManager
                    db = DatabaseManager()
                    db.initialize()
                    
                    strategy_class = TargetCalculator._load_strategy(strategy_name)
                    settings = TargetCalculator._load_strategy_settings(strategy_name)
                    
                    if strategy_class:
                        # 准备数据调用should_stop_loss和should_take_profit
                        next_stop_loss, next_take_profit = TargetCalculator._get_targets_from_strategy(
                            strategy_class, holding, current_price, settings, 
                            is_customized_sl, is_customized_tp
                        )
                except Exception as e:
                    logger.error(f"调用策略目标方法失败: {e}")
            
            return {
                'next_stop_loss': next_stop_loss,
                'next_take_profit': next_take_profit,
                'completed_stop_losses': [],
                'completed_take_profits': [],
                'is_customized': True,
                'customized_message': '自定义策略目标' if (next_stop_loss or next_take_profit) else '需要策略在should_stop_loss/should_take_profit中返回next_target'
            }
        
        # 计算已完成的止损/止盈（通过卖出历史）
        completed_stop_losses = TargetCalculator._get_completed_stop_losses(
            stop_loss_config, avg_cost, current_price, amount, operations
        )
        completed_take_profits = TargetCalculator._get_completed_take_profits(
            take_profit_config, avg_cost, current_price, amount, operations
        )
        
        # 计算下一止损
        next_stop_loss = TargetCalculator._find_next_stop_loss(
            stop_loss_config, avg_cost, completed_stop_losses
        )
        
        # 计算下一止盈
        next_take_profit = TargetCalculator._find_next_take_profit(
            take_profit_config, avg_cost, amount, completed_take_profits, current_price
        )
        
        return {
            'next_stop_loss': next_stop_loss,
            'next_take_profit': next_take_profit,
            'completed_stop_losses': completed_stop_losses,
            'completed_take_profits': completed_take_profits,
            'is_customized': False
        }
    
    @staticmethod
    def _get_completed_stop_losses(
        stop_loss_config: Dict[str, Any],
        avg_cost: float,
        current_price: float,
        current_amount: int,
        operations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        判断已完成的止损目标
        
        思路：
        1. 根据卖出历史重建每次卖出时的平均成本
        2. 如果卖出价格达到了止损目标，标记为完成
        """
        completed = []
        
        # 计算卖出历史（按时间正序）
        sell_operations = [op for op in operations if op.get('type') == 'sell']
        
        # 重建历史状态：计算每次卖出时的平均成本
        # 需要按时间正序处理
        sorted_operations = sorted(operations, key=lambda x: x.get('date', ''))
        
        historical_states = []
        temp_amount = 0
        temp_cost = 0.0
        
        for op in sorted_operations:
            if op['type'] in ['buy', 'add']:
                temp_amount += op['amount']
                temp_cost += float(op['price']) * op['amount']
            elif op['type'] == 'sell':
                if temp_amount > 0:
                    historical_avg_cost = temp_cost / temp_amount
                    historical_states.append({
                        'amount': temp_amount,
                        'avg_cost': historical_avg_cost,
                        'sell_price': float(op['price']),
                        'sell_amount': op['amount'],
                        'sell_date': op['date']
                    })
                
                # 模拟卖出
                sell_amount = op['amount']
                if temp_amount > 0:
                    historical_avg_cost = temp_cost / temp_amount
                    temp_amount -= sell_amount
                    temp_cost -= historical_avg_cost * sell_amount
        
        # 检查哪些止损目标已在历史卖出中完成
        stages = stop_loss_config.get('stages', [])
        for state in historical_states:
            for stage in stages:
                target_ratio = stage.get('ratio', 0)
                target_price = state['avg_cost'] * (1 + target_ratio)
                
                if state['sell_price'] <= target_price:
                    # 找到了已完成的止损目标
                    if not any(c.get('name') == stage.get('name') for c in completed):
                        completed.append({
                            'name': stage.get('name'),
                            'ratio': target_ratio,
                            'target_price': target_price,
                            'sell_price': state['sell_price'],
                            'sell_date': state['sell_date']
                        })
        
        return completed
    
    @staticmethod
    def _get_completed_take_profits(
        take_profit_config: Dict[str, Any],
        avg_cost: float,
        current_price: float,
        current_amount: int,
        operations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        判断已完成的止盈目标
        
        思路：
        1. 根据卖出历史重建每次卖出时的平均成本
        2. 如果卖出价格达到了止盈目标，标记为完成
        """
        completed = []
        
        stages = take_profit_config.get('stages', [])
        if not stages:
            return completed
        
        # 重建历史状态：计算每次卖出时的平均成本
        # 需要按时间正序处理
        sorted_operations = sorted(operations, key=lambda x: x.get('date', ''))
        
        historical_states = []
        temp_amount = 0
        temp_cost = 0.0
        
        for op in sorted_operations:
            if op['type'] in ['buy', 'add']:
                temp_amount += op['amount']
                temp_cost += float(op['price']) * op['amount']
            elif op['type'] == 'sell':
                if temp_amount > 0:
                    historical_avg_cost = temp_cost / temp_amount
                    historical_states.append({
                        'amount': temp_amount,
                        'avg_cost': historical_avg_cost,
                        'sell_price': float(op['price']),
                        'sell_amount': op['amount'],
                        'sell_date': op['date']
                    })
                
                # 模拟卖出
                sell_amount = op['amount']
                if temp_amount > 0:
                    historical_avg_cost = temp_cost / temp_amount
                    temp_amount -= sell_amount
                    temp_cost -= historical_avg_cost * sell_amount
        
        # 检查哪些止盈目标已在历史卖出中完成
        for state in historical_states:
            for stage in stages:
                target_ratio = stage.get('ratio', 0)
                target_price = state['avg_cost'] * (1 + target_ratio)
                target_sell_ratio = stage.get('sell_ratio', 0.2)
                
                # 计算本次卖出占当时仓位的比例
                sell_ratio_in_state = state['sell_amount'] / state['amount'] if state['amount'] > 0 else 0
                
                # 判断条件：价格达标就认为完成（卖出比例是目标，不是硬性要求）
                if state['sell_price'] >= target_price:
                    # 找到了已完成的止盈目标
                    if not any(c.get('name') == stage.get('name') for c in completed):
                        completed.append({
                            'name': stage.get('name'),
                            'ratio': target_ratio,
                            'target_price': target_price,
                            'sell_price': state['sell_price'],
                            'sell_date': state['sell_date'],
                            'sell_ratio': target_sell_ratio,
                            'actual_sell_ratio': sell_ratio_in_state
                        })
        
        return completed
    
    @staticmethod
    def _find_next_stop_loss(
        stop_loss_config: Dict[str, Any],
        avg_cost: float,
        completed: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """找到下一个止损目标"""
        completed_names = {c.get('name') for c in completed}
        
        # 先检查break_even和dynamic
        break_even = stop_loss_config.get('break_even')
        if break_even and break_even.get('name') not in completed_names:
            target_price = avg_cost * (1 + break_even.get('ratio', 0))
            return {
                'name': 'break_even',
                'type': 'stop_loss',
                'ratio': break_even.get('ratio', 0),
                'target_price': target_price,
                'target_amount': None  # 需要所有仓位
            }
        
        dynamic = stop_loss_config.get('dynamic')
        if dynamic and dynamic.get('name') not in completed_names:
            target_price = avg_cost * (1 + dynamic.get('ratio', -0.1))
            return {
                'name': 'dynamic',
                'type': 'stop_loss',
                'ratio': dynamic.get('ratio', -0.1),
                'target_price': target_price,
                'target_amount': None
            }
        
        # 检查stages
        stages = stop_loss_config.get('stages', [])
        for stage in stages:
            if stage.get('name') not in completed_names:
                target_ratio = stage.get('ratio', 0)
                target_price = avg_cost * (1 + target_ratio)
                return {
                    'name': stage.get('name'),
                    'type': 'stop_loss',
                    'ratio': target_ratio,
                    'target_price': target_price,
                    'target_amount': None
                }
        
        return None
    
    @staticmethod
    def _find_next_take_profit(
        take_profit_config: Dict[str, Any],
        avg_cost: float,
        current_amount: int,
        completed: List[Dict[str, Any]],
        current_price: float = None
    ) -> Optional[Dict[str, Any]]:
        """找到下一个止盈目标"""
        completed_names = {c.get('name') for c in completed}
        
        stages = take_profit_config.get('stages', [])
        for stage in stages:
            if stage.get('name') not in completed_names:
                target_ratio = stage.get('ratio', 0)
                target_price = avg_cost * (1 + target_ratio)
                sell_ratio = stage.get('sell_ratio', 1.0)
                
                # 计算需要卖出的数量（A股100股最小单位）
                target_amount = int(current_amount * sell_ratio) if current_amount else 0
                # 四舍五入到100股的倍数
                target_amount_rounded = round(target_amount / 100) * 100
                
                # 判断价格是否已达标
                price_reached = current_price is not None and current_price >= target_price
                
                result = {
                    'name': stage.get('name'),
                    'type': 'take_profit',
                    'ratio': target_ratio,
                    'target_price': target_price,
                    'sell_ratio': sell_ratio,
                    'target_amount': target_amount_rounded,
                    'price_reached': price_reached  # 价格是否已达标
                }
                
                if price_reached:
                    result['status'] = f'价格已达标，还需卖出{target_amount_rounded}股'
                
                return result
        
        return None

    
    @staticmethod
    def _load_strategy(strategy_name: str):
        """加载策略类"""
        try:
            strategy_module_path = f"app.core.modules.analyzer.strategy.{strategy_name}.{strategy_name}"
            strategy_module = importlib.import_module(strategy_module_path)
            
            # 获取策略类（通常是模块中唯一的类）
            for attr_name in dir(strategy_module):
                attr = getattr(strategy_module, attr_name)
                if (isinstance(attr, type) and 
                    hasattr(attr, '__bases__') and 
                    any('BaseStrategy' in str(base) for base in attr.__bases__)):
                    return attr
            return None
        except Exception as e:
            logger.error(f"加载策略{strategy_name}失败: {e}")
            return None
    
    @staticmethod
    def _load_strategy_settings(strategy_name: str) -> Dict[str, Any]:
        """加载策略配置"""
        try:
            settings_module_path = f"app.core.modules.analyzer.strategy.{strategy_name}.settings"
            settings_module = importlib.import_module(settings_module_path)
            return getattr(settings_module, 'settings', {})
        except Exception as e:
            logger.error(f"加载策略{strategy_name}配置失败: {e}")
            return {}
    
    @staticmethod
    def _get_targets_from_strategy(
        strategy_class, 
        holding: Dict[str, Any], 
        current_price: float, 
        settings: Dict[str, Any],
        need_stop_loss: bool,
        need_take_profit: bool
    ) -> tuple:
        """
        通过调用策略的should_stop_loss/should_take_profit获取目标信息
        
        Args:
            strategy_class: 策略类
            holding: 持仓信息
            current_price: 当前价格
            settings: 策略配置
            need_stop_loss: 是否需要止损目标
            need_take_profit: 是否需要止盈目标
            
        Returns:
            (next_stop_loss, next_take_profit)
        """
        next_stop_loss = None
        next_take_profit = None
        
        # 构建简化的investment对象
        investment = {
            'holding': holding,
            'avg_cost': holding.get('avg_cost', 0),
            'amount': holding.get('amount', 0),
            'stock_id': holding.get('stock_id')
        }
        
        # 构建简化的record_of_today
        record_of_today = {
            'close': current_price,
            'date': holding.get('date')  # 可能需要从其他地方获取
        }
        
        # 构建stock_info
        stock_info = {
            'id': holding.get('stock_id')
        }
        
        # 构建required_data（简化版）
        required_data = {}
        
        try:
            # 尝试调用get_next_stop_loss_target和get_next_take_profit_target
            # 传递strategy_class参数以便调用子类重写的方法
            if need_stop_loss and hasattr(strategy_class, 'get_next_stop_loss_target'):
                next_stop_loss = strategy_class.get_next_stop_loss_target(
                    stock_info, record_of_today, investment, required_data, settings, strategy_class
                )
            
            if need_take_profit and hasattr(strategy_class, 'get_next_take_profit_target'):
                next_take_profit = strategy_class.get_next_take_profit_target(
                    stock_info, record_of_today, investment, required_data, settings, strategy_class
                )
            
            # 调用should_*方法获取target_info
            if need_stop_loss and hasattr(strategy_class, 'should_stop_loss'):
                _, result = strategy_class.should_stop_loss(
                    stock_info, record_of_today, investment, required_data, settings
                )
                if isinstance(result, dict) and 'target_info' in result:
                    next_stop_loss = result['target_info']
                else:
                    # 策略重写了should_stop_loss但没有返回target_info，这是必须的
                    logger.error(f"策略 {strategy_class.__name__} 的 should_stop_loss 方法没有返回 'target_info' 字段")
                    logger.error("对于is_customized=True的止损配置，必须返回target_info字段")
                    logger.error("格式: return (bool, {**investment, 'target_info': {'target_price': x, 'current_price': y}})")
                    raise ValueError(
                        f"策略 {strategy_class.__name__} 的 should_stop_loss 方法必须返回 'target_info' 字段，"
                        "格式: {**investment, 'target_info': {'target_price': x, 'current_price': y}}"
                    )
            
            if need_take_profit and hasattr(strategy_class, 'should_take_profit'):
                _, result = strategy_class.should_take_profit(
                    stock_info, record_of_today, investment, required_data, settings
                )
                if isinstance(result, dict) and 'target_info' in result:
                    next_take_profit = result['target_info']
                else:
                    # 策略重写了should_take_profit但没有返回target_info，这是必须的
                    logger.error(f"策略 {strategy_class.__name__} 的 should_take_profit 方法没有返回 'target_info' 字段")
                    logger.error("对于is_customized=True的止盈配置，必须返回target_info字段")
                    logger.error("格式: return (bool, {**investment, 'target_info': {'target_price': x, 'current_price': y}})")
                    raise ValueError(
                        f"策略 {strategy_class.__name__} 的 should_take_profit 方法必须返回 'target_info' 字段，"
                        "格式: {**investment, 'target_info': {'target_price': x, 'current_price': y}}"
                    )
                    
        except Exception as e:
            logger.error(f"调用策略方法获取目标失败: {e}")
        
        return next_stop_loss, next_take_profit

