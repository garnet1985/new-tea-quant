from utils.db.db_model import BaseTableModel

class CorporateFinanceModel(BaseTableModel):
    """Corporate Finance模型"""
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        self.is_base_table = True

    # ------------------------ helpers ------------------------
    def _to_quarter(self, s: str) -> str:
        """支持 YYYYQn 或 YYYYMMDD -> YYYYQn。"""
        if not s:
            return s
        s = str(s).strip()
        if 'Q' in s:
            return s
        if len(s) == 8 and s.isdigit():
            year = s[:4]
            month = int(s[4:6])
            q = (month - 1) // 3 + 1
            return f"{year}Q{q}"
        raise ValueError("start_date/end_date must be YYYYQ[1-4] or YYYYMMDD")

    def _build_condition(self, stock_id: str = None, start_date: str = None, end_date: str = None):
        conditions = []
        params = []
        if stock_id:
            conditions.append("id = %s")
            params.append(stock_id)
        if start_date:
            start_q = self._to_quarter(start_date)
            conditions.append("quarter >= %s")
            params.append(start_q)
        if end_date:
            end_q = self._to_quarter(end_date)
            conditions.append("quarter <= %s")
            params.append(end_q)
        condition = " AND ".join(conditions) if conditions else "1=1"
        return condition, tuple(params)

    def _select_fields(self, records, fields):
        if not records:
            return []
        base = ['id', 'quarter']
        cols = base + fields
        return [ {k: r.get(k) for k in cols} for r in records ]

    # ------------------------ APIs ------------------------
    def load_all(self, stock_id: str = None, start_date: str = None, end_date: str = None):
        condition, params = self._build_condition(stock_id, start_date, end_date)
        return self.load(condition=condition, params=params, order_by="id ASC, quarter ASC")

    def load_growth_indicators(self, stock_id: str = None, start_date: str = None, end_date: str = None):
        fields = [
            'or_yoy', 'netprofit_yoy', 'basic_eps_yoy', 'dt_eps_yoy', 'tr_yoy'
        ]
        condition, params = self._build_condition(stock_id, start_date, end_date)
        recs = self.load(condition=condition, params=params, order_by="id ASC, quarter ASC")
        return self._select_fields(recs, fields)

    def load_profit_indicators(self, stock_id: str = None, start_date: str = None, end_date: str = None):
        fields = [
            'eps', 'dt_eps', 'roe_dt', 'roe', 'roa', 'netprofit_margin',
            'gross_profit_margin', 'op_income', 'roic', 'ebit', 'ebitda',
            'dtprofit_to_profit', 'profit_dedt'
        ]
        condition, params = self._build_condition(stock_id, start_date, end_date)
        recs = self.load(condition=condition, params=params, order_by="id ASC, quarter ASC")
        return self._select_fields(recs, fields)

    def load_cashflow_indicators(self, stock_id: str = None, start_date: str = None, end_date: str = None):
        fields = [
            'ocfps', 'fcff', 'fcfe'
        ]
        condition, params = self._build_condition(stock_id, start_date, end_date)
        recs = self.load(condition=condition, params=params, order_by="id ASC, quarter ASC")
        return self._select_fields(recs, fields)

    # solvency：偿还能力 T.T
    def load_solvency_indicators(self, stock_id: str = None, start_date: str = None, end_date: str = None):
        fields = [
            'netdebt', 'debt_to_eqt', 'debt_to_assets', 'interestdebt',
            'assets_to_eqt', 'quick_ratio', 'current_ratio'
        ]
        condition, params = self._build_condition(stock_id, start_date, end_date)
        recs = self.load(condition=condition, params=params, order_by="id ASC, quarter ASC")
        return self._select_fields(recs, fields)

    def load_operation_indicators(self, stock_id: str = None, start_date: str = None, end_date: str = None):
        fields = ['ar_turn']
        condition, params = self._build_condition(stock_id, start_date, end_date)
        recs = self.load(condition=condition, params=params, order_by="id ASC, quarter ASC")
        return self._select_fields(recs, fields)

    def load_asset_indicators(self, stock_id: str = None, start_date: str = None, end_date: str = None):
        fields = ['bps']
        condition, params = self._build_condition(stock_id, start_date, end_date)
        recs = self.load(condition=condition, params=params, order_by="id ASC, quarter ASC")
        return self._select_fields(recs, fields)