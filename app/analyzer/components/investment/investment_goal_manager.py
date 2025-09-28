#!/usr/bin/env python3
"""
投资目标管理器 - 全局可复用的投资目标解析和结算类
"""
from typing import Dict, Any, List, Tuple
from copy import deepcopy

from loguru import logger
from app.analyzer.components.enum.common_enum import InvestmentResult
from app.analyzer.analyzer_service import AnalyzerService


class InvestmentGoalManager:
    """投资目标管理器 - 处理投资目标的检查、触发和结算"""
    
    def __init__(self, goal_config: Dict[str, Any]):
        """
        初始化投资目标管理器
        
        Args:
            goal_config: 投资目标配置，包含take_profit和stop_loss配置
        """
        self.goal_config = goal_config
        self.take_profit_config = goal_config.get('take_profit', {})
        self.stop_loss_config = goal_config.get('stop_loss', {})
    
    def create_investment_targets(self) -> Dict[str, Any]:
        """
        创建投资目标状态结构
        
        Returns:
            投资目标状态字典
        """
        return {
            'investment_ratio_left': 1.0,  # 剩余投资比例
            'is_breakeven': False,          # 是否启用保本止损
            'is_dynamic_stop_loss': False,  # 是否启用动态止损
            'last_highest_close': 0.0,      # 动态止损的最高价
            'all': {
                'stop_loss': deepcopy(self.stop_loss_config),
                'take_profit': deepcopy(self.take_profit_config.get('stages', []))
            },
            'completed': [],  # 已触发的目标
        }
    
    @staticmethod
    def check_targets(investment: Dict[str, Any], current_record: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        检查投资目标是否触发
        
        Args:
            investment: 投资对象，包含targets状态
            current_record: 当前交易日记录
            
        Returns:
            (是否投资结束, 更新后的投资对象)
        """
        # 先检查止盈目标（重要：止盈会触发止损策略）
        investment = InvestmentGoalManager._check_take_profit_targets(investment, current_record)
        
        # 再检查止损目标
        investment = InvestmentGoalManager._check_stop_loss_targets(investment, current_record)
        
        # 检查是否投资结束
        is_investment_ended = investment['targets']['investment_ratio_left'] <= 0
        if is_investment_ended:
            investment['end_date'] = current_record['date']
        
        return is_investment_ended, investment
    
    @staticmethod
    def _check_take_profit_targets(investment: Dict[str, Any], current_record: Dict[str, Any]) -> Dict[str, Any]:
        """检查止盈目标"""
        price_today = current_record['close']
        purchase_price = investment['purchase_price']
        targets = investment['targets']['all']['take_profit']
        
        # 检查固定天数到期
        investment = InvestmentGoalManager._check_fixed_days_expiry(investment, current_record)
        
        for i, target in enumerate(targets):
            # 跳过已触发的目标
            if target.get('is_achieved', False):
                continue
            
            # 检查是否达到止盈价格
            target_price = purchase_price * (1 + target['ratio'])
            if price_today >= target_price:
                # 计算卖出比例
                sell_ratio = target['sell_ratio']
                
                # 更新剩余投资比例
                investment['targets']['investment_ratio_left'] -= sell_ratio
                
                # 标记目标为已触发
                targets[i]['is_achieved'] = True
                
                # 创建已结算目标
                settled_target = InvestmentGoalManager._create_settled_target(
                    target, sell_ratio, price_today - purchase_price, 
                    price_today, current_record['date']
                )
                investment['targets']['completed'].append(settled_target)
                
                # 检查是否需要设置止损策略
                if target.get('set_stop_loss') == 'break_even':
                    investment['targets']['is_breakeven'] = True
                elif target.get('set_stop_loss') == 'dynamic':
                    investment['targets']['is_dynamic_stop_loss'] = True
                    investment['targets']['last_highest_close'] = price_today
        
        return investment
    
    @staticmethod
    def _check_stop_loss_targets(investment: Dict[str, Any], current_record: Dict[str, Any]) -> Dict[str, Any]:
        """检查止损目标"""
        price_today = current_record['close']
        purchase_price = investment['purchase_price']
        stop_loss_config = investment['targets']['all']['stop_loss']
        
        # 检查固定天数到期
        investment = InvestmentGoalManager._check_fixed_days_expiry(investment, current_record)
        
        # 检查动态止损
        if investment['targets']['is_dynamic_stop_loss']:
            investment = InvestmentGoalManager._check_dynamic_stop_loss(investment, current_record, stop_loss_config)
        
        # 检查保本止损
        elif investment['targets']['is_breakeven']:
            investment = InvestmentGoalManager._check_breakeven_stop_loss(investment, current_record, stop_loss_config)
        
        # 检查普通止损阶段
        else:
            investment = InvestmentGoalManager._check_stage_stop_loss(investment, current_record, stop_loss_config)
        
        return investment
    
    @staticmethod
    def _check_dynamic_stop_loss(investment: Dict[str, Any], current_record: Dict[str, Any], stop_loss_config: Dict[str, Any]) -> Dict[str, Any]:
        """检查动态止损"""
        price_today = current_record['close']
        purchase_price = investment['purchase_price']
        
        # 更新最高价
        if 'last_highest_close' not in investment['targets']:
            investment['targets']['last_highest_close'] = price_today
        else:
            investment['targets']['last_highest_close'] = max(
                investment['targets']['last_highest_close'], price_today
            )
        
        # 检查动态止损触发
        dynamic_config = stop_loss_config.get('dynamic', {})
        if not dynamic_config.get('is_achieved', False):
            highest_price = investment['targets']['last_highest_close']
            dynamic_stop_price = highest_price * (1 + dynamic_config['ratio'])
            
            if price_today <= dynamic_stop_price:
                sell_ratio = min(1.0, investment['targets']['investment_ratio_left'])
                investment['targets']['investment_ratio_left'] -= sell_ratio
                
                # 标记动态止损为已触发
                dynamic_config['is_achieved'] = True
                
                # 创建已结算目标
                settled_target = InvestmentGoalManager._create_settled_target(
                    dynamic_config, sell_ratio, price_today - purchase_price,
                    price_today, current_record['date']
                )
                investment['targets']['completed'].append(settled_target)
        
        return investment
    
    @staticmethod
    def _check_breakeven_stop_loss(investment: Dict[str, Any], current_record: Dict[str, Any], stop_loss_config: Dict[str, Any]) -> Dict[str, Any]:
        """检查保本止损"""
        price_today = current_record['close']
        purchase_price = investment['purchase_price']
        
        breakeven_config = stop_loss_config.get('break_even', {})
        if not breakeven_config.get('is_achieved', False):
            if price_today <= purchase_price:
                sell_ratio = min(1.0, investment['targets']['investment_ratio_left'])
                investment['targets']['investment_ratio_left'] -= sell_ratio
                
                # 标记保本止损为已触发
                breakeven_config['is_achieved'] = True
                
                # 创建已结算目标
                settled_target = InvestmentGoalManager._create_settled_target(
                    breakeven_config, sell_ratio, price_today - purchase_price,
                    price_today, current_record['date']
                )
                investment['targets']['completed'].append(settled_target)
        
        return investment
    
    @staticmethod
    def _check_stage_stop_loss(investment: Dict[str, Any], current_record: Dict[str, Any], stop_loss_config: Dict[str, Any]) -> Dict[str, Any]:
        """检查普通止损阶段"""
        price_today = current_record['close']
        purchase_price = investment['purchase_price']
        
        stages = stop_loss_config.get('stages', [])
        for i, stage in enumerate(stages):
            if stage.get('is_achieved', False):
                continue
            
            stage_price = purchase_price * (1 + stage['ratio'])
            if price_today <= stage_price:
                sell_ratio = min(1.0, investment['targets']['investment_ratio_left'])
                investment['targets']['investment_ratio_left'] -= sell_ratio
                
                # 标记阶段为已触发
                stages[i]['is_achieved'] = True
                
                # 创建已结算目标
                settled_target = InvestmentGoalManager._create_settled_target(
                    stage, sell_ratio, price_today - purchase_price,
                    price_today, current_record['date']
                )
                investment['targets']['completed'].append(settled_target)
                break  # 只触发第一个满足条件的止损
        
        return investment
    
    @staticmethod
    def _create_settled_target(target_config: Dict[str, Any], sell_ratio: float, 
                             profit: float, exit_price: float, exit_date: str) -> Dict[str, Any]:
        """
        创建已结算的目标对象
        
        Args:
            target_config: 目标配置
            sell_ratio: 实际卖出比例
            profit: 利润
            exit_price: 退出价格
            exit_date: 退出日期
            
        Returns:
            已结算的目标对象
        """
        settled_target = target_config.copy()
        settled_target['is_achieved'] = True
        settled_target['sell_ratio'] = sell_ratio
        settled_target['profit'] = profit
        settled_target['exit_price'] = exit_price
        settled_target['exit_date'] = exit_date
        return settled_target
    
    @staticmethod
    def _check_fixed_days_expiry(investment: Dict[str, Any], current_record: Dict[str, Any]) -> Dict[str, Any]:
        """检查固定天数到期"""
        # 检查是否已经设置了固定天数到期标记
        if investment['targets'].get('is_fixed_days_expired', False):
            return investment
        
        # 获取投资开始日期和当前日期
        start_date = investment['start_date']
        current_date = current_record['date']
        
        # 计算投资天数
        days_elapsed = InvestmentGoalManager._calculate_days_between(start_date, current_date)
        
        # 检查stages配置中的fixed_days
        stages_config = investment['targets']['all'].get('stages', {})
        fixed_days = stages_config.get('fixed_days')
        
        if fixed_days and days_elapsed >= fixed_days:
            
            # 获取结算配置 - sell_ratio 和 close_invest 只能出现一个
            close_invest = stages_config.get('close_invest', False)  # 布尔值，默认不全额结算
            sell_ratio = stages_config.get('sell_ratio', 0.0)  # 数值，默认不结算
            
            # 确定实际结算比例
            if close_invest:
                # close_invest 为 True 时，全额结算
                actual_sell_ratio = 1.0
            elif sell_ratio > 0:
                # 使用指定的 sell_ratio
                actual_sell_ratio = sell_ratio
            else:
                # 默认不结算
                actual_sell_ratio = 0.0
            
            # 计算当前价格和利润
            price_today = current_record['close']
            purchase_price = investment['purchase_price']
            profit = (price_today - purchase_price) * actual_sell_ratio
            
            # 更新剩余投资比例
            investment['targets']['investment_ratio_left'] -= actual_sell_ratio
            
            # 创建固定天数到期的结算目标
            fixed_days_target = {
                'type': 'fixed_days_expiry',
                'ratio': 0,  # 固定天数到期不基于价格比例
                'sell_ratio': actual_sell_ratio,
                'is_achieved': True
            }
            
            # 使用统一的结算目标创建函数
            settled_target = InvestmentGoalManager._create_settled_target(
                fixed_days_target, actual_sell_ratio, profit,
                price_today, current_date
            )
            investment['targets']['completed'].append(settled_target)
        
        return investment
    
    @staticmethod
    def _calculate_days_between(start_date: str, end_date: str) -> int:
        """计算两个日期之间的天数"""
        from datetime import datetime
        
        try:
            start = datetime.strptime(start_date, '%Y%m%d')
            end = datetime.strptime(end_date, '%Y%m%d')
            return (end - start).days
        except ValueError:
            logger.warning(f"日期格式错误: {start_date} 或 {end_date}")
            return 0