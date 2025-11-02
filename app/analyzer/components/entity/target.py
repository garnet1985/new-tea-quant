from ast import Dict
from enum import Enum
from typing import Any


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

        self.content = {
            **stage,
            'target_type': target_type.value,
            'purchase_price': purchase_price,
            'start_date': date,
            'end_date': '',
            'target_price': purchase_price * (1 + stage.get('ratio', 0)),
            'amplitude_tracking': self.update_amplitude_tracking(record_of_today),
            'extra_fields': extra_fields,
        }

        self.start_record_ref = record_of_today
        self.tracker = {
            'last_check_date': record_of_today.get('date', ''),
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
        last_check_date = self.tracker.get('last_check_date', '')
        if date <= last_check_date:
            return

        close_price = record_of_today.get('close', 0)
        self.tracker['last_check_date'] = date
        if close_price >= self.amplitude_tracking['max_close_reached']['price']:
            self.amplitude_tracking['max_close_reached']['price'] = close_price
            self.amplitude_tracking['max_close_reached']['date'] = date
            self.amplitude_tracking['max_close_reached']['ratio'] = (close_price - self.start_record_ref.get('close', 0)) / self.start_record_ref.get('close', 0)
            
        if close_price < self.amplitude_tracking['min_close_reached']['price']:
            self.amplitude_tracking['min_close_reached']['price'] = close_price
            self.amplitude_tracking['min_close_reached']['date'] = date
            self.amplitude_tracking['min_close_reached']['ratio'] = (close_price - self.start_record_ref.get('close', 0)) / self.start_record_ref.get('close', 0)


    def is_achieved(self, record_of_today: Dict[str, Any]):
        if self.is_achieved:
            return True
        else:
            date = record_of_today.get('date', '')
            last_check_date = self.tracker.get('last_check_date', '')
            if date <= last_check_date:
                return False

            close_price = record_of_today.get('close', 0)
            if close_price >= self.content['target_price']:
                self.settle(record_of_today)
                return True
        return False

    def is_dynamic_loss_achieved(self, record_of_today: Dict[str, Any], tracking: Dict[str, Any]):
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

    def settle(self, record_of_today: Dict[str, Any]):
        if self.is_achieved:
            return
        else:
            self.is_achieved = True
            self.content['end_date'] = record_of_today.get('date')
            self.content['sell_price'] = record_of_today.get('close')
            self.content['sell_date'] = record_of_today.get('date')
            self.content['profit'] = self.content['sell_price'] - self.content['purchase_price']
            self.content['weighted_profit'] = self.content['profit'] * self.content['sell_ratio']
        return self

    def to_dict(self):
        return self.content