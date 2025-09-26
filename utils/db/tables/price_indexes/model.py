from utils.db.db_model import BaseTableModel



class PriceIndexesModel(BaseTableModel):
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True

    def _build_date_condition(self, start_date: str = None, end_date: str = None):
        conditions = []
        params = []
        if start_date:
            conditions.append("date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("date <= %s")
            params.append(end_date)
        condition = " AND ".join(conditions) if conditions else "1=1"
        return condition, tuple(params)

    def load_CPI(self, start_date: str = None, end_date: str = None):
        condition, params = self._build_date_condition(start_date, end_date)
        return self.load(condition=condition, params=params, order_by="date ASC")

    def load_PPI(self, start_date: str = None, end_date: str = None):
        condition, params = self._build_date_condition(start_date, end_date)
        return self.load(condition=condition, params=params, order_by="date ASC")

    def load_PMI(self, start_date: str = None, end_date: str = None):
        condition, params = self._build_date_condition(start_date, end_date)
        return self.load(condition=condition, params=params, order_by="date ASC")

    def load_money_supply(self, start_date: str = None, end_date: str = None):
        condition, params = self._build_date_condition(start_date, end_date)
        return self.load(condition=condition, params=params, order_by="date ASC")

    def load_price_indexes(self, start_date: str = None, end_date: str = None):
        condition, params = self._build_date_condition(start_date, end_date)
        return self.load(condition=condition, params=params, order_by="date ASC")