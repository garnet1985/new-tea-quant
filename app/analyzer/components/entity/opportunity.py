from typing import Any, Dict


class Opportunity:

    def __init__(self, 
        stock: Dict[str, Any],
        record_of_today: Dict[str, Any],
        price_tolerance: float = 0.01,
        lower_bound: float = None,
        upper_bound: float = None,
        extra_fields: Dict[str, Any] = None
    ):
        if lower_bound is None:
            lower_bound = record_of_today * (1 - price_tolerance)
        if upper_bound is None:
            upper_bound = record_of_today * (1 + price_tolerance)

        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

        self.price = record_of_today.get('close', 0) or 0
        self.date = record_of_today.get('date') or ''

        self.extra_fields = extra_fields or {}
        self.ref_record = record_of_today

    def to_dict(self):
        data = {
            'stock': self.stock,
            'date': self.date,
            'price': self.price,
            'lower_bound': self.lower_bound,
            'upper_bound': self.upper_bound,
            'extra_fields': self.extra_fields,
        }
        return data

    def link_simulation_summary(self, simulation_summary: Dict[str, Any]):
        # todo: link simulation summary to opportunity
        pass

    def present(self):
        # todo: present opportunity
        pass