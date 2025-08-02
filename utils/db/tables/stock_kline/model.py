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

    def get_all_klines_by_term(self, stock_code: str, term: str, order_by: str = 'ASC'):
        sql = f"""
                SELECT * FROM stock_kline WHERE code = %s AND term = %s ORDER BY date {order_by}
            """
        return self.execute_raw_query(sql, (stock_code, term))

    def get_most_recent_one_by_term(self, stock_code: str, term: str):
        sql = f"""
                SELECT * FROM stock_kline WHERE code = %s AND term = %s ORDER BY date DESC LIMIT 1
            """
        return self.execute_raw_query(sql, (stock_code, term))
    
