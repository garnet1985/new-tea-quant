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

        self.content = {
            **stage,
            'is_achieved': False,
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


    def to_dict(self):
        return self.content