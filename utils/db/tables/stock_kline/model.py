"""
Stock Kline 模型
提供股票K线相关的特定方法
"""
from utils.db.db_model import BaseTableModel
from loguru import logger


class StockKlineModel(BaseTableModel):
    """股票K线表自定义模型"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True

    def get_all_klines_by_term(self, stock_id: str, term: str, order: str = 'ASC'):
        return self.load("id = %s AND term = %s", (stock_id, term), order_by=f"date {order}")

    def get_most_recent_one_by_term(self, stock_id: str, term: str):
        return self.load_one("id = %s AND term = %s ORDER BY date DESC LIMIT 1", (stock_id, term))
    
    def get_by_date(self, stock_id: str, trade_date: str):
        return self.load_one("id = %s AND date = %s", (stock_id, trade_date))    
