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


    # @staticmethod
    # def settle_investment(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
    #     """
    #     结算投资，计算最终收益和结果
    #     """
    #     logger.info(f"结算投资: {investment}")
    #     if not isinstance(investment, dict):
    #         return False, investment

    #     # 判定是否已结束（比例是否卖完）
    #     targets = investment.get('targets', {})
    #     investment_ratio_left = targets.get('investment_ratio_left', 0)
    #     is_settled = investment_ratio_left <= 0

    #     # 如果结束且没有结束日期，则补充
    #     if is_settled and 'end_date' not in investment and isinstance(record_of_today, dict):
    #         end_date = record_of_today.get('date')
    #         if end_date:
    #             investment['end_date'] = end_date

    #     # 汇总已完成目标收益
    #     achieved_targets = targets.get('completed', []) if isinstance(targets, dict) else []
    #     overall_profit = 0.0
    #     for t in achieved_targets:
    #         try:
    #             profit = float(t.get('profit', 0.0))
    #             sell_ratio = float(t.get('sell_ratio', 0.0))
    #             overall_profit += profit * sell_ratio
    #         except Exception:
    #             continue

    #     # 设置收益信息与结果
    #     investment['overall_profit'] = overall_profit
    #     purchase_price = float(investment.get('purchase_price', 0) or 0)
    #     investment['overall_profit_rate'] = AnalyzerService.to_ratio(overall_profit, purchase_price, 2)

    #     if overall_profit > 0:
    #         investment['result'] = InvestmentResult.WIN.value
    #     elif overall_profit < 0:
    #         investment['result'] = InvestmentResult.LOSS.value
    #     else:
    #         investment['result'] = InvestmentResult.DRAW.value if hasattr(InvestmentResult, 'DRAW') else 0

    #     return is_settled, investment
    
    # def settle_investment(self, investment: Dict[str, Any]) -> None:
    #     """
    #     结算投资，计算最终收益和结果
        
    #     Args:
    #         investment: 投资对象
    #     """
    #     purchase_price = investment['purchase_price']
    #     achieved_targets = investment['targets']['completed']
        
    #     # 计算总体收益
    #     overall_profit = 0
    #     for target in achieved_targets:
    #         overall_profit += target['profit'] * target['sell_ratio']
        
    #     # 确定投资结果
    #     if overall_profit > 0:
    #         investment['result'] = InvestmentResult.WIN.value
    #     else:
    #         investment['result'] = InvestmentResult.LOSS.value
        
    #     # 设置收益信息
    #     investment['overall_profit'] = overall_profit
    #     investment['overall_profit_rate'] = AnalyzerService.to_ratio(overall_profit, purchase_price, 2)
        
    #     # 计算目标权重和贡献
    #     for target in achieved_targets:
    #         target['weighted_profit'] = target['profit'] * target['sell_ratio']
    #         target['profit_contribution'] = target['sell_ratio']
    
    # def settle_open_investment(self, investment: Dict[str, Any], final_price: float, final_date: str) -> None:
    #     """
    #     结算未结束的投资（用于回测结束时的处理）
        
    #     Args:
    #         investment: 投资对象
    #         final_price: 最终价格
    #         final_date: 最终日期
    #     """
    #     if investment['targets']['investment_ratio_left'] > 0:
    #         purchase_price = investment['purchase_price']
    #         remaining_ratio = investment['targets']['investment_ratio_left']
    #         profit = (final_price - purchase_price) * remaining_ratio
            
    #         # 创建最终结算目标
    #         final_target = {
    #             'name': 'final_settlement',
    #             'sell_ratio': remaining_ratio,
    #             'profit': profit,
    #             'exit_price': final_price,
    #             'exit_date': final_date,
    #             'is_achieved': True
    #         }
            
    #         investment['targets']['completed'].append(final_target)
    #         investment['targets']['investment_ratio_left'] = 0
    #         investment['end_date'] = final_date
            
    #         # 重新结算投资
    #         self.settle_investment(investment)
