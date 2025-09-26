from utils.db.db_model import BaseTableModel

class GDPModel(BaseTableModel):
    """GDP模型"""
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        self.is_base_table = True

    def load_GDP(self, start_quarter: str = None, end_quarter: str = None):
        """
        加载GDP数据（季度）。
        参数名: start_quarter / end_quarter；格式: YYYYQ{1-4}；均可选，不传表示不限制。
        """
        if not start_quarter and not end_quarter:
            return self.load_all()

        # 校验季度格式 YYYYQ{1-4}
        def _is_valid_quarter(q: str) -> bool:
            import re
            return bool(q) and re.match(r"^\d{4}Q[1-4]$", q)

        if start_quarter and not _is_valid_quarter(start_quarter):
            raise ValueError("start_quarter must be in format YYYYQ[1-4]")
        if end_quarter and not _is_valid_quarter(end_quarter):
            raise ValueError("end_quarter must be in format YYYYQ[1-4]")

        conditions = []
        params = []

        if start_quarter:
            conditions.append("quarter >= %s")
            params.append(start_quarter)
        if end_quarter:
            conditions.append("quarter <= %s")
            params.append(end_quarter)

        condition = " AND ".join(conditions) if conditions else "1=1"
        return self.load(condition=condition, params=tuple(params), order_by="quarter ASC")