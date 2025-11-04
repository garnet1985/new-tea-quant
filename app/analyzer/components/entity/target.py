from enum import Enum
from typing import Any, Dict, Tuple

from loguru import logger

from utils.date.date_utils import DateUtils


class InvestmentTarget:

    class TargetType(Enum):
        TAKE_PROFIT = 'take_profit'
        STOP_LOSS = 'stop_loss'
        EXPIRED = 'expired'

    def __init__(self, 
        target_type: TargetType, 
        start_record: Dict[str, Any], 
        stage: Dict[str, Any], 
        extra_fields: Dict[str, Any] = None
    ):
        self._validate_stage(stage)

        self.target_type = target_type

        self.purchase_price = start_record.get('close', 0)

        self.is_achieved = False
        self.start_record_ref = start_record
        self.tracker = {
            'last_updated_date': start_record.get('date', ''),
            'stage': stage,
            'extra_fields': extra_fields,
        }

        self.content = {
            'target_type': target_type.value,
            'name': stage.get('name', ''),
            'sell_ratio': stage.get('sell_ratio', 0),
            'sell_price': 0,
            'sell_date': '',
            'sell_ratio': 0,
            'profit': 0,
            'weighted_profit': 0,
            'profit_ratio': 0,
            'target_price': 0
        }

        if stage.get('ratio', 0) > 0:
            self.content['ratio'] = stage.get('ratio', 0)
            self.content['target_price'] = self.purchase_price * (1 + self.content['ratio'])

        if self.tracker.get('close_invest', False):
            self.content['sell_ratio'] = 1.0
        else:
            self.content['sell_ratio'] = stage.get('sell_ratio', 0)
    
    def _validate_stage(self, stage: Dict[str, Any]):
        if 'name' not in stage:
            raise ValueError(f"stage must have 'name' field: {stage}")

        if 'sell_ratio' not in stage and 'close_invest' not in stage:
            raise ValueError(f"stage must have either 'sell_ratio' or 'close_invest' field: {stage}")

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


    def is_complete(self, record_of_today: Dict[str, Any], remaining_investment_ratio: float = 1.0) -> Tuple[bool, float]:
        """检查目标是否完成，如果完成则立即settle"""
        if self.is_achieved:
            # return False to avoid push into completed list twice
            return False, remaining_investment_ratio

        if remaining_investment_ratio <= 0:
            # return False to avoid push into completed list twice
            return False, remaining_investment_ratio

        if DateUtils.is_before_or_same_day(record_of_today.get('date'), self.tracker.get('last_updated_date')):
            # return False to avoid push into completed list twice
            return False, remaining_investment_ratio

        close_price = record_of_today.get('close', 0)
        target_price = self.content['target_price']
        
        is_completed = False
        # 根据目标类型检查
        if self.target_type == self.TargetType.TAKE_PROFIT:
            # 止盈：价格 >= 目标价格
            if close_price >= target_price:
                is_completed = True
        elif self.target_type == self.TargetType.STOP_LOSS:
            # 止损：价格 <= 目标价格
            if close_price <= target_price:
                is_completed = True
        
        # 如果完成，立即settle
        if is_completed:
            # 计算sell_ratio
            sell_ratio = self.calc_sell_ratio(remaining_investment_ratio)
            self.settle(record_of_today, sell_ratio)
            return True, remaining_investment_ratio - sell_ratio
        
        return False, remaining_investment_ratio

    def calc_sell_ratio(self, remaining_investment_ratio: float):
        if self.tracker['stage'].get('close_invest'):
            return remaining_investment_ratio
        else:
            sell_ratio = self.content.get('sell_ratio', 0)
            if sell_ratio > remaining_investment_ratio:
                return remaining_investment_ratio
            else:
                return sell_ratio
        

    def is_dynamic_loss_complete(self, record_of_today: Dict[str, Any], tracking: Dict[str, Any]):
        if self.is_achieved:
            # return False to avoid push into completed list twice
            return False
        else:
            date = record_of_today.get('date', '')
            last_updated_date = self.tracker.get('last_updated_date', '')
            if DateUtils.is_before_or_same_day(date, last_updated_date):
                # return False to avoid push into completed list twice
                return False

            self.tracker['last_updated_date'] = date
            close_price = record_of_today.get('close', 0)
            if close_price < self.content['target_price']:
                self.settle(record_of_today)
                return True
        return False

    def settle(self, record_of_today: Dict[str, Any], calculated_sell_ratio: float):
        if self.is_achieved:
            return
        else:
            self.is_achieved = True
            self.content['sell_price'] = record_of_today.get('close')
            self.content['sell_date'] = record_of_today.get('date')
            self.content['sell_ratio'] = calculated_sell_ratio
            self.content['profit'] = self.content['sell_price'] - self.purchase_price
            self.content['weighted_profit'] = self.content['profit'] * self.content['sell_ratio']
            self.content['profit_ratio'] = self.content['profit'] / self.purchase_price
            if self.content['target_price'] == 0:
                # the expiration target will fit this scenario:
                self.content['target_price'] = self.purchase_price
            if self.tracker['extra_fields'] is not None:
                self.content['extra_fields'] = self.tracker['extra_fields']
        return self

    def to_dict(self):
        
        return self.content