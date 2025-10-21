#!/usr/bin/env python3
"""
投资目标管理器 - 全局可复用的投资目标解析和结算类
"""
from typing import Dict, Any, List, Tuple
from copy import deepcopy

from loguru import logger
from app.analyzer.enums import InvestmentResult
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
        self.is_customized = goal_config.get('is_customized', False)
    
    def create_investment_targets(self) -> Dict[str, Any]:
        """
        创建投资目标状态结构
        
        Returns:
            投资目标状态字典
        """
        if self.is_customized:
            # 对于customized goal，创建简化的targets结构
            return {
                'investment_ratio_left': 1.0,  # 剩余投资比例
                'is_customized': True,          # 标记为customized goal
                'is_breakeven': False,          # 是否启用保本止损
                'is_dynamic_stop_loss': False,  # 是否启用动态止损
                'last_highest_close': 0.0,      # 动态止损的最高价
                'all': {
                    # customized goal不使用传统的stop_loss和take_profit配置
                    'stop_loss': {},
                    'take_profit': [],
                },
                'fixed_days': {},               # customized goal不使用固定天数
                'fixed_trading_days': {},
                'fixed_days_canceled': False,
                'fixed_trading_days_canceled': False,
                # 运行时状态
                'trading_days_elapsed': 0,
                'last_checked_date': None,
                'completed': [],  # 已触发的目标
            }
        else:
            # 传统的goal系统
            return {
                'investment_ratio_left': 1.0,  # 剩余投资比例
                'is_customized': False,         # 标记为传统goal
                'is_breakeven': False,          # 是否启用保本止损
                'is_dynamic_stop_loss': False,  # 是否启用动态止损
                'last_highest_close': 0.0,      # 动态止损的最高价
                'all': {
                    'stop_loss': deepcopy(self.stop_loss_config),
                    # 止盈阶段列表
                    'take_profit': deepcopy(self.take_profit_config.get('stages', [])),
                },
                # 固定平仓（goal级别，可选）
                'fixed_days': deepcopy(self.goal_config.get('fixed_days')),
                'fixed_trading_days': deepcopy(self.goal_config.get('fixed_trading_days')),
                'fixed_days_canceled': False,
                'fixed_trading_days_canceled': False,
                # 运行时状态
                'trading_days_elapsed': 0,
                'last_checked_date': None,
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
        # 对于customized goal，不进行传统的目标检查
        if investment['targets'].get('is_customized', False):
            # customized goal的结算逻辑由策略的should_settle_investment方法处理
            # 这里只需要保持investment对象不变，返回False表示未结束
            return False, investment
        
        # 先检查 goal 级别固定平仓（自然日/交易日）
        investment = InvestmentGoalManager._check_goal_level_fixed_days(investment, current_record)
        
        # 若未到期，再检查止盈（止盈可能切换止损策略）
        if investment['targets']['investment_ratio_left'] > 0:
            investment = InvestmentGoalManager._check_take_profit_targets(investment, current_record)
        
        # 若仍未结束，再检查止损
        if investment['targets']['investment_ratio_left'] > 0:
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
        investment = InvestmentGoalManager._check_goal_level_fixed_days(investment, current_record)
        
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
                
                # 止盈阶段可调整 goal 级 fixed_days / fixed_trading_days
                # extend_fixed_days: 正为增加，负为减少；cancel_fixed_days: True 则取消生效
                if 'extend_fixed_days' in target:
                    try:
                        delta_days = int(target['extend_fixed_days'])
                        base_days = investment['targets'].get('fixed_days')
                        if base_days is not None:
                            investment['targets']['fixed_days'] = max(0, int(base_days) + delta_days)
                    except Exception:
                        pass
                if target.get('cancel_fixed_days') is True:
                    investment['targets']['fixed_days_canceled'] = True
                if 'extend_fixed_trading_days' in target:
                    try:
                        delta_tdays = int(target['extend_fixed_trading_days'])
                        base_tdays = investment['targets'].get('fixed_trading_days')
                        if base_tdays is not None:
                            investment['targets']['fixed_trading_days'] = max(0, int(base_tdays) + delta_tdays)
                    except Exception:
                        pass
                if target.get('cancel_fixed_trading_days') is True:
                    investment['targets']['fixed_trading_days_canceled'] = True
        
        return investment
    
    @staticmethod
    def _check_stop_loss_targets(investment: Dict[str, Any], current_record: Dict[str, Any]) -> Dict[str, Any]:
        """检查止损目标"""
        price_today = current_record['close']
        purchase_price = investment['purchase_price']
        stop_loss_config = investment['targets']['all']['stop_loss']
        
        # 检查固定天数到期
        investment = InvestmentGoalManager._check_goal_level_fixed_days(investment, current_record)
        
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
    def _check_goal_level_fixed_days(investment: Dict[str, Any], current_record: Dict[str, Any]) -> Dict[str, Any]:
        """检查 goal 级别的 fixed_days / fixed_trading_days 到期结算"""
        # 若被取消，则不再生效
        fixed_days = None if investment['targets'].get('fixed_days_canceled') else investment['targets'].get('fixed_days')
        fixed_trading_days = None if investment['targets'].get('fixed_trading_days_canceled') else investment['targets'].get('fixed_trading_days')
        if fixed_days is None and fixed_trading_days is None:
            return investment
        
        start_date = investment['start_date']
        current_date = current_record['date']
        
        # 自然日
        days_elapsed = InvestmentGoalManager._calculate_days_between(start_date, current_date)
        
        # 交易日（按不同日期计数）
        if investment['targets'].get('last_checked_date') != current_date:
            investment['targets']['trading_days_elapsed'] = investment['targets'].get('trading_days_elapsed', 0) + 1
            investment['targets']['last_checked_date'] = current_date
        trading_days_elapsed = investment['targets'].get('trading_days_elapsed', 0)
        
        natural_expired = fixed_days is not None and days_elapsed >= int(fixed_days)
        trading_expired = fixed_trading_days is not None and trading_days_elapsed >= int(fixed_trading_days)
        if not natural_expired and not trading_expired:
            return investment
        
        # 到期全额结算
        actual_sell_ratio = min(1.0, investment['targets']['investment_ratio_left'])
        if actual_sell_ratio <= 0:
            return investment
        price_today = current_record['close']
        purchase_price = investment['purchase_price']
        profit = (price_today - purchase_price) * actual_sell_ratio
        
        investment['targets']['investment_ratio_left'] -= actual_sell_ratio
        investment['targets']['investment_ratio_left'] = max(0.0, investment['targets']['investment_ratio_left'])
        fixed_target = {
            'type': 'fixed_days_expiry',
            'ratio': 0,
            'sell_ratio': actual_sell_ratio,
            'is_achieved': True,
            'mode': 'trading_days' if trading_expired else 'natural_days'
        }
        settled_target = InvestmentGoalManager._create_settled_target(
            fixed_target, actual_sell_ratio, profit, price_today, current_date
        )
        investment['targets']['completed'].append(settled_target)
        return investment
    
    @staticmethod
    def _calculate_days_between(start_date: str, end_date: str) -> int:
        """计算两个日期之间的天数"""
        from utils.date.date_utils import DateUtils
        
        try:
            return DateUtils.get_duration_in_days(start_date, end_date, DateUtils.DATE_FORMAT_YYYYMMDD)
        except ValueError:
            logger.warning(f"日期格式错误: {start_date} 或 {end_date}")
            return 0