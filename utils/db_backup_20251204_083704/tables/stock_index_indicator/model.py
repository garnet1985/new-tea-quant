from utils.db.db_model import BaseTableModel

class StockIndexIndicatorModel(BaseTableModel):
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True

    # 统一的条件构建（按id与日期范围；若term需支持，可再扩展）
    def _build_condition(self, index_id: str = None, start_date: str = None, end_date: str = None):
        conditions = []
        params = []
        if index_id:
            conditions.append("id = %s")
            params.append(index_id)
        if start_date:
            conditions.append("date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("date <= %s")
            params.append(end_date)
        condition = " AND ".join(conditions) if conditions else "1=1"
        return condition, tuple(params)

    # 基础API
    def load_all(self, start_date: str = None, end_date: str = None):
        condition, params = self._build_condition(None, start_date, end_date)
        return self.load(condition=condition, params=params, order_by="id ASC, date ASC")

    def load_index(self, index_id: str, start_date: str = None, end_date: str = None):
        condition, params = self._build_condition(index_id, start_date, end_date)
        return self.load(condition=condition, params=params, order_by="date ASC")

    # 便捷API（常用指数）
    def load_sh_index(self, start_date: str = None, end_date: str = None):
        return self.load_index('000001.SH', start_date, end_date)

    def load_sz_index(self, start_date: str = None, end_date: str = None):
        return self.load_index('399001.SZ', start_date, end_date)

    def load_hs_300(self, start_date: str = None, end_date: str = None):
        return self.load_index('000300.SH', start_date, end_date)

    def load_cyb_index(self, start_date: str = None, end_date: str = None):
        return self.load_index('399006.SZ', start_date, end_date)

    def load_kc_50(self, start_date: str = None, end_date: str = None):
        return self.load_index('000688.SH', start_date, end_date)