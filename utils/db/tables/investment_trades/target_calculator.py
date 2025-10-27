"""
投资目标计算器 - 计算下一止损和下一止盈目标
"""
from typing import Dict, Any, List, Optional
from loguru import logger
import json
import importlib


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
            # 对于customized策略，尝试调用策略的get_target方法
            next_stop_loss = None
            next_take_profit = None
            
            if strategy_name:
                try:
                    # 加载策略
                    from utils.db.db_manager import DatabaseManager
                    db = DatabaseManager()
                    db.initialize()
                    
                    strategy_class = TargetCalculator._load_strategy(strategy_name)
                    settings = TargetCalculator._load_strategy_settings(strategy_name)
                    
                    if strategy_class:
                        # 调用策略的目标方法
                        if is_customized_sl:
                            next_stop_loss = strategy_class.get_stop_loss_target(
                                holding, current_price, settings
                            )
                        
                        if is_customized_tp:
                            next_take_profit = strategy_class.get_take_profit_target(
                                holding, current_price, settings
                            )
                except Exception as e:
                    logger.error(f"调用策略目标方法失败: {e}")
            
            return {
                'next_stop_loss': next_stop_loss,
                'next_take_profit': next_take_profit,
                'completed_stop_losses': [],
                'completed_take_profits': [],
                'is_customized': True,
                'customized_message': '自定义策略目标' if (next_stop_loss or next_take_profit) else '需要策略实现get_stop_loss_target/get_take_profit_target方法'
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
            take_profit_config, avg_cost, amount, completed_take_profits
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
        historical_states = []
        temp_amount = 0
        temp_cost = 0.0
        
        for op in operations:
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
        historical_states = []
        temp_amount = 0
        temp_cost = 0.0
        
        for op in operations:
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
                
                if state['sell_price'] >= target_price:
                    # 找到了已完成的止盈目标
                    if not any(c.get('name') == stage.get('name') for c in completed):
                        completed.append({
                            'name': stage.get('name'),
                            'ratio': target_ratio,
                            'target_price': target_price,
                            'sell_price': state['sell_price'],
                            'sell_date': state['sell_date'],
                            'sell_ratio': stage.get('sell_ratio', 0.2)
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
        completed: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """找到下一个止盈目标"""
        completed_names = {c.get('name') for c in completed}
        
        stages = take_profit_config.get('stages', [])
        for stage in stages:
            if stage.get('name') not in completed_names:
                target_ratio = stage.get('ratio', 0)
                target_price = avg_cost * (1 + target_ratio)
                sell_ratio = stage.get('sell_ratio', 1.0)
                
                # 计算需要卖出的数量
                target_amount = int(current_amount * sell_ratio) if current_amount else 0
                
                return {
                    'name': stage.get('name'),
                    'type': 'take_profit',
                    'ratio': target_ratio,
                    'target_price': target_price,
                    'sell_ratio': sell_ratio,
                    'target_amount': target_amount
                }
        
        return None

