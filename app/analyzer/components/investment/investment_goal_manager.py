#!/usr/bin/env python3
"""
投资目标管理器 - 全局可复用的投资目标解析和结算类
"""
from typing import Dict, Any, List, Tuple, Optional

from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.components.base_strategy import BaseStrategy


class InvestmentGoalManager:
    """投资目标管理器 - 处理投资目标的检查、触发和结算"""
    
    @staticmethod
    def is_investment_settled(record_of_today: Dict[str, Any], investment: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any], strategy_class: Any) -> Tuple[bool, Dict[str, Any]]:
        """检查投资目标是否触发"""
        InvestmentGoalManager._update_targets(record_of_today, investment, required_data, strategy_class, settings)

        if InvestmentGoalManager._is_investment_completed(investment):
            return True, BaseStrategy.to_settled_investment(record_of_today, investment)
        
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
        take_profit_info = investment.get('targets_tracking', {}).get('take_profit', {})
        stop_loss_info = investment.get('targets_tracking', {}).get('stop_loss', {})

        has_achieved_target = False
        completed_targets = []

        # 检查是否有customized止盈
        targets = take_profit_info.get('targets', [])

        if take_profit_info.get('is_customized', False):
            has_achieved_target, completed_targets = strategy_class.is_customized_take_profit_achieved(record_of_today, required_data, targets, investment, settings)
            InvestmentGoalManager._validate_customized_targets(targets, completed_targets)
        else:
            has_achieved_target, completed_targets = InvestmentGoalManager._check_targets_completion(record_of_today, targets, investment, strategy_class)
        
        if has_achieved_target:
            investment = InvestmentGoalManager._settle_targets(completed_targets, investment, record_of_today)
            if InvestmentGoalManager._is_investment_completed(investment):
                return

        # 检查是否有customized止损
        has_achieved_target = False
        completed_targets = []

        targets = stop_loss_info.get('targets', [])
        if stop_loss_info.get('is_customized', False):
            has_achieved_target, completed_targets = strategy_class.is_customized_stop_loss_achieved(record_of_today, required_data, targets, investment, settings)
            InvestmentGoalManager._validate_customized_targets(targets, completed_targets)
        else:
            has_achieved_target,completed_targets = InvestmentGoalManager._check_stop_loss_targets(record_of_today, targets, investment, strategy_class)

        if has_achieved_target:
            investment = InvestmentGoalManager._settle_targets(completed_targets, investment, record_of_today)


    @staticmethod
    def _check_stop_loss_targets(record_of_today: Dict[str, Any], targets: List[Dict[str, Any]], investment: Dict[str, Any], strategy_class: Any) -> Tuple[bool, List[Dict[str, Any]]]:
        """检查止损目标"""
        completed_targets = []
        has_achieved_target = False

        # 检查动态止损
        if investment['targets_tracking'].get('dynamic_loss', {}).get('is_enabled'):
            has_achieved_target, target = InvestmentGoalManager._check_dynamic_stop_loss(record_of_today, investment, strategy_class)
            if target:
                completed_targets.append(target)

        if has_achieved_target:
            return True, completed_targets


        # 检查保本止损
        if investment['targets_tracking'].get('protected_loss', {}).get('is_enabled'):
            has_achieved_target, target = InvestmentGoalManager._check_protected_loss(record_of_today, investment, strategy_class)
            if target:
                completed_targets.append(target)

        if has_achieved_target:
            return True, completed_targets


        # 检查普通止损阶段 - 使用传入的targets参数，而不是重新获取
        has_achieved_target, completed_targets = InvestmentGoalManager._check_targets_completion(record_of_today, targets, investment, strategy_class)
        
        return has_achieved_target, completed_targets

    @staticmethod
    def _check_targets_completion(record_of_today: Dict[str, Any], targets: List[Dict[str, Any]], investment: Dict[str, Any], strategy_class: Any) -> Tuple[bool, List[Dict[str, Any]]]:
        """检查目标"""
        completed_targets = []
        has_achieved_target = False
        
        if not targets:
            return False, []
        
        for target in targets:
            is_completed = InvestmentGoalManager._check_target_completion(record_of_today, target, investment)
            if is_completed:
                completed_targets.append(target)
                has_achieved_target = True
                if target.get('actions'):
                    investment = InvestmentGoalManager._trigger_actions(target.get('actions'), record_of_today, investment, strategy_class)
        
        return has_achieved_target, completed_targets

    @staticmethod
    def _check_target_completion(record_of_today: Dict[str, Any], target: Dict[str, Any], investment: Dict[str, Any]) -> bool:
        """检查目标的实现情况
        
        根据 target_type 判断目标类型：
        - 'take_profit': 止盈目标，检查 price >= target_price
        - 'stop_loss': 止损目标，检查 price <= target_price
        """
        if target.get('is_achieved'):
            return True
        
        price_of_today = record_of_today.get('close', 0)
        target_price = target.get('target_price', 0)
        target_type = target.get('target_type', 'take_profit')  # 默认为止盈
        
        if target_price <= 0 or price_of_today <= 0:
            return False
        
        # 根据 target_type 判断是止盈还是止损
        if target_type == 'take_profit':
            # 止盈：价格上涨到目标价格
            if price_of_today >= target_price:
                InvestmentGoalManager._settle_target(record_of_today, target, investment)
                return True
        elif target_type == 'stop_loss':
            # 止损：价格下跌到目标价格
            if price_of_today <= target_price:
                InvestmentGoalManager._settle_target(record_of_today, target, investment)
                return True
        
        return False

    @staticmethod
    def _check_dynamic_stop_loss(record_of_today: Dict[str, Any], investment: Dict[str, Any], strategy_class: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """检查动态止损"""
        allowed_lowest_price_ratio = investment.get('targets_tracking', {}).get('dynamic_loss', {}).get('ratio')
        last_highest_close = investment.get('targets_tracking', {}).get('dynamic_loss', {}).get('last_highest_close')
        allowed_lowest_price = last_highest_close * (1 + allowed_lowest_price_ratio)

        if record_of_today['close'] <= allowed_lowest_price:
            target = investment['targets_tracking']['dynamic_loss'].get('target')
            if target:
                InvestmentGoalManager._settle_target(record_of_today, target, investment)
                return True, target
        return False, None

    
    @staticmethod
    def _check_protected_loss(record_of_today: Dict[str, Any], investment: Dict[str, Any], strategy_class: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """检查保本止损"""
        protected_loss_info = investment['targets_tracking'].get('protected_loss', {})
        protected_loss_ratio = protected_loss_info.get('ratio')
        
        if protected_loss_ratio is None:
            return False, None
            
        protected_loss_price = investment['purchase_price'] * (1 + protected_loss_ratio)

        if record_of_today['close'] <= protected_loss_price:
            target = protected_loss_info.get('target')
            if target:
                InvestmentGoalManager._settle_target(record_of_today, target, investment)
                return True, target
        return False, None


    @staticmethod
    def _settle_targets(completed_targets: List[Dict[str, Any]], investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> Dict[str, Any]:
        """结算目标"""
        for target in completed_targets:
            InvestmentGoalManager._settle_target(record_of_today, target, investment)
        return investment

    @staticmethod
    def _settle_target(record_of_today: Dict[str, Any], target: Dict[str, Any], investment: Dict[str, Any]) -> None:
        """结算目标"""
        target['is_achieved'] = True
        target['sell_price'] = record_of_today['close']
        target['sell_date'] = record_of_today['date']
        target['profit'] = target['sell_price'] - investment['purchase_price']
        if target.get('close_invest'):
            target['sell_ratio'] = investment['targets_tracking']['investment_ratio_left']
        else:
            target['sell_ratio'] = min(investment['targets_tracking']['investment_ratio_left'], target.get('sell_ratio', 0))
        
        # 更新剩余投资比例
        investment['targets_tracking']['investment_ratio_left'] -= target['sell_ratio']
        investment['targets_tracking']['completed'].append(target)

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

    @staticmethod
    def _trigger_actions(actions: List[Dict[str, Any]], record_of_today: Dict[str, Any], investment: Dict[str, Any], strategy_class: Any) -> Dict[str, Any]:
        """触发actions"""
        for action in actions:
            if action.get('set_stop_loss') == 'protected':
                investment['targets_tracking']['protected_loss']['is_enabled'] = True
                from app.analyzer.components.base_strategy import BaseStrategy
                investment['targets_tracking']['protected_loss']['target'] = strategy_class.create_target(
                    stage = {
                        'name': 'protected_loss',
                        'ratio': 0,
                        'close_invest': True,
                    },
                    record_of_today = record_of_today,
                    target_type = BaseStrategy.TargetType.STOP_LOSS
                )

            elif action.get('set_stop_loss') == 'dynamic':
                investment['targets_tracking']['dynamic_loss']['is_enabled'] = True
                investment['targets_tracking']['dynamic_loss']['last_highest_close'] = record_of_today['close']
                from app.analyzer.components.base_strategy import BaseStrategy
                investment['targets_tracking']['dynamic_loss']['target'] = strategy_class.create_target(
                    stage = {
                        'name': 'dynamic_loss',
                        'ratio': 0,
                        'close_invest': True,
                    },
                    record_of_today = record_of_today,
                    target_type = BaseStrategy.TargetType.STOP_LOSS
                )

        return investment

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

    @staticmethod
    def _validate_customized_targets(updated_targets: List[Dict[str, Any]], completed_targets: List[Dict[str, Any]]) -> None:
        """验证自定义目标"""
        for updated_target in updated_targets:
            if updated_target.get('target_price') is None or updated_target.get('target_price') == 0:
                raise ValueError(f"target_price is required to update to non zero value in your strategy class, please check is_customized_stop_loss_achieved or is_customized_take_profit_achieved function.")
            if updated_target.get('sell_ratio') is None or updated_target.get('sell_ratio') == 0:
                raise ValueError(f"sell_ratio is required to update to non zero value in your strategy class, please check is_customized_stop_loss_achieved or is_customized_take_profit_achieved function.")

        for completed_target in completed_targets:
            if completed_target.get('sell_price') is None or completed_target.get('target_price') == 0:
                raise ValueError(f"target_price is required to be non zero value in your strategy class, please check is_customized_stop_loss_achieved or is_customized_take_profit_achieved function.")
            if completed_target.get('sell_date') is None or completed_target.get('sell_date') == '':
                raise ValueError(f"sell_date is required to be non empty value in your strategy class, please check is_customized_stop_loss_achieved or is_customized_take_profit_achieved function.")
            if completed_target.get('sell_ratio') is None or completed_target.get('sell_ratio') == 0:
                raise ValueError(f"sell_ratio is required to be non zero value in your strategy class, please check is_customized_stop_loss_achieved or is_customized_take_profit_achieved function.")