from enum import Enum
from typing import Any, Dict


class InvestmentTarget:

    class TargetType(Enum):
        TAKE_PROFIT = 'take_profit'
        STOP_LOSS = 'stop_loss'

    def __init__(self, 
        target_type: TargetType, 
        record_of_today: Dict[str, Any], 
        stage: Dict[str, Any], 
        extra_fields: Dict[str, Any] = None
    ):
        self._validate_stage(stage)

        self.target_type = target_type

        purchase_price = record_of_today.get('close', 0)
        date = record_of_today.get('date', '')

        self.is_achieved = False
        self.start_record_ref = record_of_today
        self.tracker = {
            'last_check_date': record_of_today.get('date', ''),
        }

        self.content = {
            **stage,
            'target_type': target_type.value,
            'purchase_price': purchase_price,
            'start_date': date,
            'end_date': '',
            'target_price': purchase_price * (1 + stage.get('ratio', 0)),
            'amplitude_tracking': {
                'max_close_reached': { 'price': purchase_price, 'date': date, 'ratio': 0 },
                'min_close_reached': { 'price': purchase_price, 'date': date, 'ratio': 0 },
            },
            'extra_fields': extra_fields,
        }
    
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


    def update_amplitude_tracking(self, record_of_today: Dict[str, Any]):
        date = record_of_today.get('date', '')
        close_price = record_of_today.get('close', 0)
        purchase_price = self.start_record_ref.get('close', 0)
        
        last_check_date = self.tracker.get('last_check_date', '')
        if date <= last_check_date:
            return self.content['amplitude_tracking']

        self.tracker['last_check_date'] = date
        amplitude_tracking = self.content['amplitude_tracking']
        
        if close_price >= amplitude_tracking['max_close_reached']['price']:
            amplitude_tracking['max_close_reached']['price'] = close_price
            amplitude_tracking['max_close_reached']['date'] = date
            amplitude_tracking['max_close_reached']['ratio'] = (close_price - purchase_price) / purchase_price if purchase_price > 0 else 0
            
        if close_price < amplitude_tracking['min_close_reached']['price']:
            amplitude_tracking['min_close_reached']['price'] = close_price
            amplitude_tracking['min_close_reached']['date'] = date
            amplitude_tracking['min_close_reached']['ratio'] = (close_price - purchase_price) / purchase_price if purchase_price > 0 else 0
        
        return amplitude_tracking


    def is_complete(self, record_of_today: Dict[str, Any], remaining_investment_ratio: float = 1.0):
        """检查目标是否完成，如果完成则立即settle"""
        if self.is_achieved:
            return True
        
        date = record_of_today.get('date', '')
        last_check_date = self.tracker.get('last_check_date', '')
        if date <= last_check_date:
            return False

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
            sell_ratio = self._calc_sell_ratio(remaining_investment_ratio)
            self.settle(record_of_today, sell_ratio)
            return True
        
        return False

    def _calc_sell_ratio(self, remaining_investment_ratio: float):
        if self.content.get('close_invest'):
            return remaining_investment_ratio
        else:
            sell_ratio = self.content.get('sell_ratio', 0)
            if sell_ratio > remaining_investment_ratio:
                return remaining_investment_ratio
            else:
                return sell_ratio
        

    def is_dynamic_loss_complete(self, record_of_today: Dict[str, Any], tracking: Dict[str, Any]):
        if self.is_achieved:
            return True
        else:
            date = record_of_today.get('date', '')
            last_check_date = self.tracker.get('last_check_date', '')
            if date <= last_check_date:
                return False

            close_price = record_of_today.get('close', 0)
            if close_price < self.content['target_price']:
                self.settle(record_of_today)
                return True
        return False

    def settle(self, record_of_today: Dict[str, Any], safe_sell_ratio: float = 1.0):
        if self.is_achieved:
            return
        else:
            self.is_achieved = True
            self.content['end_date'] = record_of_today.get('date')
            self.content['sell_price'] = record_of_today.get('close')
            self.content['sell_date'] = record_of_today.get('date')
            self.content['sell_ratio'] = safe_sell_ratio
            self.content['profit'] = self.content['sell_price'] - self.content['purchase_price']
            self.content['weighted_profit'] = self.content['profit'] * self.content['sell_ratio']
        return self

    def to_dict(self):
        return self.content