from utils.db.db_model import BaseTableModel

class LPRModel(BaseTableModel):
    """LPR模型"""
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        self.is_base_table = True

    def load_LPR(self, start_date: str = None, end_date: str = None):
        """
        加载LPR数据（日度）。参数格式: YYYYMMDD；不传表示不限制。
        """
        if not start_date and not end_date:
            return self.load_all(order_by="date ASC")

        conditions = []
        params = []
        if start_date:
            conditions.append("date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("date <= %s")
            params.append(end_date)
        condition = " AND ".join(conditions) if conditions else "1=1"
        return self.load(condition=condition, params=tuple(params), order_by="date ASC")