from enum import Enum
from typing import Any, Dict, List, Tuple

from loguru import logger

from app.core.utils.date.date_utils import DateUtils


class InvestmentTarget:

    class TargetType(Enum):
        TAKE_PROFIT = 'take_profit'
        STOP_LOSS = 'stop_loss'
        EXPIRED = 'expired'
        OPEN = 'open'

    class TargetPriority(Enum):
        CUSTOMIZED_TAKE_PROFIT_BASE = 0      # 自定义止盈: 0-99
        NORMAL_TAKE_PROFIT_BASE = 100        # 普通止盈: 100-199
        PROTECT_LOSS = 200                   # 保护止损: 200 (优先于普通止损)
        DYNAMIC_LOSS = 300                   # 动态止损: 300 (优先于普通止损)
        CUSTOMIZED_STOP_LOSS_BASE = 400      # 自定义止损: 400-499
        NORMAL_STOP_LOSS_BASE = 500          # 普通止损: 500-599
        EXPIRATION = 900                     # 过期: 900 (最后检查)

    def __init__(self, 
        target_type: TargetType, 
        start_record: Dict[str, Any], 
        stage: Dict[str, Any], 
        extra_fields: Dict[str, Any] = None,
        is_customized: bool = False,
        priority: int = 999,
        is_enabled: bool = True,
    ):
        self.target_type = target_type
        self.is_customized = is_customized
        self.priority = priority
        self.is_enabled = is_enabled

        self._validate_stage(stage)

        self.is_settled = False
        self.start_record_ref = start_record
        self.tracker = {
            'last_updated_date': start_record.get('date', ''),
            'stage': stage,
            'extra_fields': extra_fields,
        }

        self.content = {
            'name': stage.get('name', ''),
            'target_type': target_type.value,
            'sell_price': 0,
            'sell_date': '',
            'sell_ratio': self.tracker['stage'].get('sell_ratio', 0),
            'profit': 0,
            'weighted_profit': 0,
            'profit_ratio': 0,
            'target_price': 0
        }

        ratio = stage.get('ratio', None)
        if ratio is not None:
            self.tracker['stage']['ratio'] = ratio
            self.content['target_price'] = self.start_record_ref.get('close', 0) * (1 + ratio)

        if self.tracker['stage'].get('close_invest', False):
            self.content['sell_ratio'] = 1.0
        else:
            self.content['sell_ratio'] = self.tracker['stage'].get('sell_ratio', 0)
    
    def _validate_stage(self, stage: Dict[str, Any]):
        if 'name' not in stage:
            raise ValueError(f"stage must have 'name' field: {stage}")

        if 'sell_ratio' not in stage and 'close_invest' not in stage:
            raise ValueError(f"stage must have either 'sell_ratio' or 'close_invest' field: {stage}")

        if self.target_type in [self.TargetType.TAKE_PROFIT, self.TargetType.STOP_LOSS] and 'ratio' not in stage:
            raise ValueError(f"stage must have 'ratio' field for {self.target_type.value} target: {stage}")

    @staticmethod
    def create_stage(name: str, target_settings: Dict[str, Any]):
        stage = {
            'name': name,
        }
        if target_settings.get('ratio', None) is not None:
            stage['ratio'] = target_settings.get('ratio', 0)
        if target_settings.get('sell_ratio', None) is not None:
            stage['sell_ratio'] = target_settings.get('sell_ratio', 0)
        if target_settings.get('close_invest', None) is not None:
            stage['close_invest'] = target_settings.get('close_invest', False)
        return stage

    
    def _is_checking_ready_to_start(self, record_of_today: Dict[str, Any], remaining_investment_ratio: float):
        if self.is_settled:
            return False
        if remaining_investment_ratio <= 0:
            return False
        if DateUtils.is_before_or_same_day(record_of_today.get('date'), self.tracker.get('last_updated_date')):
            return False
        return True


    def is_achieved(self, 
            record_of_today: Dict[str, Any], 
            remaining_investment_ratio: float,
            required_data: Dict[str, Any] = None,
            strategy_class: Any = None,
            settings: Dict[str, Any] = None,
        ) -> Tuple[bool, float]:
        """检查目标是否完成，如果完成则立即settle"""
        if not self._is_checking_ready_to_start(record_of_today, remaining_investment_ratio):
            return False, remaining_investment_ratio
        
        is_achieved = False
        if self.is_customized:
            is_achieved, remaining_investment_ratio = self._is_customized_target_complete(record_of_today, required_data, remaining_investment_ratio, strategy_class, settings)
        else:
            # 根据目标类型检查
            is_achieved = self._is_target_complete(record_of_today)

        self.tracker['last_updated_date'] = record_of_today.get('date')
        # 如果完成，立即settle
        if is_achieved:
            # 计算sell_ratio
            sell_ratio = self.calc_sell_ratio(remaining_investment_ratio)
            self.settle(record_of_today, sell_ratio)
            return True, remaining_investment_ratio - sell_ratio
        return False, remaining_investment_ratio

    def _is_target_complete(self, record_of_today: Dict[str, Any]) -> bool:
        close_price = record_of_today.get('close', 0)
        target_price = self.content['target_price']
        if self.target_type == self.TargetType.TAKE_PROFIT:
            # 止盈：价格 >= 目标价格
            if close_price >= target_price:
                return True
        elif self.target_type == self.TargetType.STOP_LOSS:
            # 止损：价格 <= 目标价格
            if close_price <= target_price:
                return True
        return False

    def _is_customized_target_complete(self, 
            record_of_today: Dict[str, Any], 
            required_data: Dict[str, Any], 
            remaining_investment_ratio: float,
            strategy_class: Any,
            settings: Dict[str, Any],
        ) -> Tuple[bool, float]:
        if self.target_type == self.TargetType.TAKE_PROFIT:
            return strategy_class.is_customized_take_profit_target_complete(self, record_of_today, required_data, remaining_investment_ratio, settings)
        elif self.target_type == self.TargetType.STOP_LOSS:
            return strategy_class.is_customized_stop_loss_target_complete(self, record_of_today, required_data, remaining_investment_ratio, settings)
        return False, remaining_investment_ratio

    def is_dynamic_loss_complete(self, record_of_today: Dict[str, Any], remaining_investment_ratio: float) -> Tuple[bool, float]:
        if not self._is_checking_ready_to_start(record_of_today, remaining_investment_ratio):
            return False, remaining_investment_ratio

        self.tracker['last_updated_date'] = record_of_today.get('date')
        price_of_today = record_of_today.get('close', 0)

        if price_of_today < self.content['target_price']:
            sell_ratio = self.calc_sell_ratio(remaining_investment_ratio)
            self.settle(record_of_today, sell_ratio)
            return True, remaining_investment_ratio - sell_ratio
        else:
            new_target_price = price_of_today * (1 + self.tracker['stage'].get('ratio', 0))
            if new_target_price > self.content['target_price']:
                self.content['target_price'] = new_target_price
                return False, remaining_investment_ratio
            else:
                return False, remaining_investment_ratio

    def check_expiration(self, record_of_today: Dict[str, Any], investment_start_date: str) -> bool:
        """
        检查是否过期（仅用于 EXPIRED 类型的 target）
        
        Args:
            record_of_today: 当前交易日记录
            investment_start_date: 投资开始日期
            
        Returns:
            bool: 是否已过期
        """
        if self.target_type != self.TargetType.EXPIRED:
            return False
        
        extra = self.tracker.get('extra_fields')
        if not extra:
            return False
        
        # 更新已过时间
        if extra.get('is_trading_period', True):
            # 按交易日计数
            extra['time_elapsed'] = extra.get('time_elapsed', 0) + 1
        else:
            # 按自然日计数
            extra['time_elapsed'] = DateUtils.get_duration_in_days(
                investment_start_date,
                record_of_today.get('date'),
                DateUtils.DATE_FORMAT_YYYYMMDD
            )
        
        # 检查是否达到阈值
        fixed_period = extra.get('fixed_period', 0)
        return extra['time_elapsed'] >= fixed_period

    def calc_sell_ratio(self, remaining_investment_ratio: float):
        if self.tracker['stage'].get('close_invest'):
            return remaining_investment_ratio
        else:
            sell_ratio = self.content.get('sell_ratio', 0)
            if sell_ratio > remaining_investment_ratio:
                return remaining_investment_ratio
            else:
                return sell_ratio

    def settle(self, record_of_today: Dict[str, Any], calculated_sell_ratio: float):
        if self.is_settled:
            return
        else:
            self.is_settled = True
            self.content['sell_price'] = record_of_today.get('close')
            self.content['sell_date'] = record_of_today.get('date')
            self.content['sell_ratio'] = calculated_sell_ratio
            self.content['profit'] = self.content['sell_price'] - self.start_record_ref.get('close', 0)
            self.content['weighted_profit'] = self.content['profit'] * self.content['sell_ratio']
            self.content['profit_ratio'] = self.content['profit'] / self.start_record_ref.get('close', 0)
            if self.content['target_price'] == 0:
                # the expiration target will fit this scenario:
                self.content['target_price'] = self.start_record_ref.get('close', 0)
            if self.tracker['extra_fields'] is not None:
                self.content['extra_fields'] = self.tracker['extra_fields']
        return self

    def has_actions(self) -> bool:
        return len(self.tracker['stage'].get('actions', [])) > 0

    def get_actions(self) -> List[Dict[str, Any]]:
        return self.tracker['stage'].get('actions', [])

    def get_start_record(self) -> Dict[str, Any]:
        return self.start_record_ref

    def set_start_record(self, record):
        self.start_record_ref = record

    def to_dict(self):
        return self.content