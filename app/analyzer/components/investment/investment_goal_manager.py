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
        # self.goal_config = goal_config
        # self.take_profit_config = goal_config.get('take_profit', {})
        # self.stop_loss_config = goal_config.get('stop_loss', {})
        
        # self.is_customized_stop_loss = self.stop_loss_config.get('is_customized', False)
        # self.is_customized_take_profit = self.take_profit_config.get('is_customized', False)

    @staticmethod
    def is_investment_settled(record_of_today: Dict[str, Any], investment: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any], strategy_class: Any) -> Tuple[bool, Dict[str, Any]]:
        """检查投资目标是否触发"""
        InvestmentGoalManager._update_targets(record_of_today, investment, required_data, strategy_class, settings)

        if InvestmentGoalManager._is_investment_completed(investment):
            return True, strategy_class.to_settled_investment(record_of_today, investment)
        
        return False, investment
    
    @staticmethod
    def _update_targets(
        record_of_today: Dict[str, Any], 
        investment: Dict[str, Any], 
        required_data: Dict[str, Any], 
        strategy_class: Any, 
        settings: Dict[str, Any]
    ) -> None:
        """
        更新投资目标
        
        Args:
            record_of_today: 当前交易日记录
            investment: 投资对象，包含targets状态
            required_data: 所需数据
            settings: 策略设置
            strategy_class: 策略类
        Returns:
            (是否投资结束, 更新后的投资对象)
        """
        take_profit_info = investment['targets_tracking']['take_profit']
        stop_loss_info = investment['targets_tracking']['stop_loss']

        has_achieved_target = False
        completed_targets = []

        # 检查是否有customized止盈
        if take_profit_info['is_customized']:
            has_achieved_target, completed_targets = strategy_class.is_customized_take_profit_achieved(record_of_today, required_data, take_profit_info['targets'], investment, settings)
        else:
            targets = take_profit_info['targets']
            has_achieved_target, completed_targets = InvestmentGoalManager._check_targets_completion(record_of_today, targets, investment)
        
        if has_achieved_target:
            investment = InvestmentGoalManager._settle_targets(completed_targets, investment)
            if InvestmentGoalManager._is_investment_completed(investment):
                return

        # 检查是否有customized止损
        has_achieved_target = False
        completed_targets = []

        if stop_loss_info['is_customized']:
            has_achieved_target, completed_targets = strategy_class.is_customized_stop_loss_achieved(record_of_today, required_data, stop_loss_info['targets'], investment, settings)
        else:
            targets = stop_loss_info['targets']
            has_achieved_target,completed_targets = InvestmentGoalManager._check_stop_loss_targets(record_of_today, targets, investment)

        if has_achieved_target:
            investment = InvestmentGoalManager._settle_targets(completed_targets, investment)


    @staticmethod
    def _check_stop_loss_targets(record_of_today: Dict[str, Any], targets: List[Dict[str, Any]], investment: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """检查止损目标"""
        # 检查动态止损
        if investment['targets_tracking'].get('dynamic_loss', {}).get('is_enabled'):
            investment = InvestmentGoalManager._check_dynamic_stop_loss(record_of_today, investment)
        
        # 检查保本止损
        elif investment['targets_tracking'].get('protected_loss', {}).get('is_enabled'):
            investment = InvestmentGoalManager._check_protected_loss(record_of_today, investment)
        
        # 检查普通止损阶段
        else:
            targets = investment['targets_tracking']['stop_loss']['targets']
            investment = InvestmentGoalManager._check_targets_completion(record_of_today, targets, investment)
        
        return investment

    @staticmethod
    def _check_targets_completion(record_of_today: Dict[str, Any], targets: List[Dict[str, Any]], investment: Dict[str, Any]) -> Dict[str, Any]:
        """检查目标"""
        for target in targets:
            is_completed = InvestmentGoalManager._check_target_completion(record_of_today, target)
            if is_completed and target.get('actions'):
                investment = InvestmentGoalManager._trigger_actions(target.get('actions'), record_of_today, investment)
        return investment

    @staticmethod
    def _check_target_completion(record_of_today: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """检查目标的实现情况"""
        if target.get('is_achieved'):
            return True
        
        price_of_today = record_of_today['close']
        if price_of_today >= target['target_price']:
            target['is_achieved'] = True
            return True
        else:
            return False

    @staticmethod
    def _trigger_actions(actions: List[Dict[str, Any]], record_of_today: Dict[str, Any], investment: Dict[str, Any]) -> Dict[str, Any]:
        """触发actions"""
        for action in actions:
            if action.get('set_stop_loss') == 'protected':
                investment['targets_tracking']['protected_loss']['is_enabled'] = True

            elif action.get('set_stop_loss') == 'dynamic':
                investment['targets_tracking']['dynamic_loss']['is_enabled'] = True
                investment['targets_tracking']['dynamic_loss']['last_highest_close'] = record_of_today['close']

        return investment



    @staticmethod
    def _check_dynamic_stop_loss(record_of_today: Dict[str, Any], investment: Dict[str, Any]) -> Dict[str, Any]:
        """检查动态止损"""
        pass
        # price_today = current_record['close']
        # purchase_price = investment['purchase_price']
        
        # # 更新最高价
        # if 'last_highest_close' not in investment['targets']:
        #     investment['targets']['last_highest_close'] = price_today
        # else:
        #     investment['targets']['last_highest_close'] = max(
        #         investment['targets']['last_highest_close'], price_today
        #     )
        
        # # 检查动态止损触发
        # dynamic_config = stop_loss_config.get('dynamic', {})
        # if not dynamic_config.get('is_achieved', False):
        #     highest_price = investment['targets']['last_highest_close']
        #     dynamic_stop_price = highest_price * (1 + dynamic_config['ratio'])
            
        #     if price_today <= dynamic_stop_price:
        #         # 标记动态止损为已触发
        #         dynamic_config['is_achieved'] = True
                
        #         if dynamic_config.get('close_invest', False):
        #             # close_invest: True 表示卖掉剩余的所有仓位并关闭投资
        #             actual_sell_ratio = investment['targets']['investment_ratio_left']  # 卖出剩余的所有仓位
        #             investment['targets']['investment_ratio_left'] = 0.0
                    
        #             # 创建已结算目标
        #             settled_target = InvestmentGoalManager._create_settled_target(
        #                 dynamic_config, actual_sell_ratio, price_today - purchase_price,
        #                 price_today, current_record['date']
        #             )
        #             investment['targets']['completed'].append(settled_target)
                    
        #             # close_invest时直接返回，不再执行后续检查
        #             return investment
        #         else:
        #             # 正常的动态止损
        #             sell_ratio = min(1.0, investment['targets']['investment_ratio_left'])
        #             investment['targets']['investment_ratio_left'] -= sell_ratio
                    
        #             # 创建已结算目标
        #             settled_target = InvestmentGoalManager._create_settled_target(
        #                 dynamic_config, sell_ratio, price_today - purchase_price,
        #                 price_today, current_record['date']
        #             )
        #             investment['targets']['completed'].append(settled_target)
        
        # return investment
    
    @staticmethod
    def _check_protected_loss(record_of_today: Dict[str, Any], investment: Dict[str, Any]) -> Dict[str, Any]:
        """检查保本止损"""
        pass
        # price_today = current_record['close']
        # purchase_price = investment['purchase_price']
        
        # breakeven_config = stop_loss_config.get('break_even', {})
        # if not breakeven_config.get('is_achieved', False):
        #     if price_today <= purchase_price:
        #         # 标记保本止损为已触发
        #         breakeven_config['is_achieved'] = True
                
        #         if breakeven_config.get('close_invest', False):
        #             # close_invest: True 表示卖掉剩余的所有仓位并关闭投资
        #             actual_sell_ratio = investment['targets']['investment_ratio_left']  # 卖出剩余的所有仓位
        #             investment['targets']['investment_ratio_left'] = 0.0
                    
        #             # 创建已结算目标
        #             settled_target = InvestmentGoalManager._create_settled_target(
        #                 breakeven_config, actual_sell_ratio, price_today - purchase_price,
        #                 price_today, current_record['date']
        #             )
        #             investment['targets']['completed'].append(settled_target)
                    
        #             # close_invest时直接返回，不再执行后续检查
        #             return investment
        #         else:
        #             # 正常的保本止损
        #             sell_ratio = min(1.0, investment['targets']['investment_ratio_left'])
        #             investment['targets']['investment_ratio_left'] -= sell_ratio
                    
        #             # 创建已结算目标
        #             settled_target = InvestmentGoalManager._create_settled_target(
        #                 breakeven_config, sell_ratio, price_today - purchase_price,
        #                 price_today, current_record['date']
        #             )
        #             investment['targets']['completed'].append(settled_target)
        
        # return investment

    @staticmethod
    def _settle_target(record_of_today: Dict[str, Any], target: Dict[str, Any], investment: Dict[str, Any]) -> Dict[str, Any]:
        """检查普通止损阶段"""
        target['is_achieved'] = True
        target['sell_price'] = record_of_today['close']
        target['sell_date'] = record_of_today['date']
        target['profit'] = target['sell_price'] - investment['purchase_price']
        return target

    @staticmethod
    def _check_investment_expiration(investment: Dict[str, Any], record_of_today: Dict[str, Any], strategy_class: Any) -> Dict[str, Any]:
        # """检查 goal 级别的 fixed_days / fixed_trading_days 到期结算"""

        is_expired = False

        if not investment['targets_tracking'].get('expiration', {}).get('is_enabled'):
            return False, investment

        date_of_today = record_of_today['date']
        days_threshold = investment['targets_tracking']['expiration']['fixed_days']

        left_ratio = investment['targets_tracking']['investment_ratio_left']
        if left_ratio <= 0:
            return False, investment

        if investment['targets_tracking']['expiration']['is_trading_days']:
            investment['targets_tracking']['expiration']['elapsed_trading_days'] += 1
            if investment['targets_tracking']['expiration']['elapsed_trading_days'] >= days_threshold:
                is_expired = True
        else:
            elapsed_natural_days = AnalyzerService.calculate_days_between(investment['targets_tracking']['expiration']['start_date'], date_of_today)
            investment['targets_tracking']['expiration']['elapsed_natural_days'] = elapsed_natural_days
            if elapsed_natural_days >= days_threshold:
                is_expired = True

        if is_expired:
            investment['end_date'] = date_of_today
            investment['targets_tracking']['expiration']['end_date'] = date_of_today
            investment['is_expired'] = True
            left_ratio = investment['targets_tracking']['investment_ratio_left']
            investment['targets_tracking']['investment_ratio_left'] = 0.0

            expiry_target = strategy_class.create_expiry_target(record_of_today, left_ratio, investment['targets_tracking']['expiration'])
            expiry_target = InvestmentGoalManager._settle_target(record_of_today, expiry_target, investment)

            investment['completed'].append(expiry_target)

        return is_expired, investment

    # ================================ utils ================================
    @staticmethod
    def _is_investment_completed(investment: Dict[str, Any]) -> bool:
        """检查投资是否结束"""
        return investment['targets_tracking']['investment_ratio_left'] <= 0

    @staticmethod
    def _get_sell_ration(target: Dict[str, Any], remain_ratio: float) -> Dict[str, Any]:
        """转换为已结算目标"""
        if target.get('close_invest'):
            return remain_ratio
        else:
            return min(remain_ratio, target['sell_ratio'])
    
    @staticmethod
    def _calculate_days_between(start_date: str, end_date: str) -> int:
        """计算两个日期之间的天数"""
        from utils.date.date_utils import DateUtils
        
        try:
            return DateUtils.get_duration_in_days(start_date, end_date, DateUtils.DATE_FORMAT_YYYYMMDD)
        except ValueError:
            logger.warning(f"日期格式错误: {start_date} 或 {end_date}")
            return 0


    # def create_investment_targets(self) -> Dict[str, Any]:
    #     """
    #     创建投资目标状态结构
        
    #     Returns:
    #         投资目标状态字典
    #     """
    #     return {
    #         'investment_ratio_left': 1.0,  # 剩余投资比例
    #         'is_customized': False,         # 标记为传统goal
    #         'is_breakeven': False,          # 是否启用保本止损
    #         'is_dynamic_stop_loss': False,  # 是否启用动态止损
    #         'last_highest_close': 0.0,      # 动态止损的最高价
    #         'all': {
    #             # 支持细粒度customized的stop_loss和take_profit配置
    #             'stop_loss': deepcopy(self.stop_loss_config),
    #             'take_profit': deepcopy(self.take_profit_config.get('stages', [])),
    #         },
    #         # 固定平仓（goal级别，可选）
    #         'fixed_days': deepcopy(self.goal_config.get('fixed_days')),
    #         'fixed_trading_days': deepcopy(self.goal_config.get('fixed_trading_days')),
    #         'fixed_days_canceled': False,
    #         'fixed_trading_days_canceled': False,
    #         # 运行时状态
    #         'trading_days_elapsed': 0,
    #         'last_checked_date': None,
    #         'completed': [],  # 已触发的目标
    #         # 细粒度customized标记
    #         'is_customized_stop_loss': self.is_customized_stop_loss,
    #         'is_customized_take_profit': self.is_customized_take_profit,
    #     }

    # @staticmethod
    # def _create_settled_target(target_config: Dict[str, Any], sell_ratio: float, 
    #                          profit: float, exit_price: float, exit_date: str) -> Dict[str, Any]:
    #     """
    #     创建已结算的目标对象
        
    #     Args:
    #         target_config: 目标配置
    #         sell_ratio: 实际卖出比例
    #         profit: 利润
    #         exit_price: 退出价格
    #         exit_date: 退出日期
            
    #     Returns:
    #         已结算的目标对象
    #     """
    #     settled_target = target_config.copy()
    #     settled_target['is_achieved'] = True
    #     settled_target['sell_ratio'] = sell_ratio
    #     settled_target['profit'] = profit
    #     settled_target['exit_price'] = exit_price
    #     settled_target['exit_date'] = exit_date
    #     return settled_target