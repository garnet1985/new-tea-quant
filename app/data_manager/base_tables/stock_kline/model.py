"""
股票K线数据 Model
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel


class StockKlineModel(DbBaseModel):
    """股票K线数据 Model"""
    
    def __init__(self, db=None):
        super().__init__('stock_kline', db)
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有K线"""
        return self.load("id = %s", (stock_id,), order_by="date ASC")
    
    def load_by_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的K线"""
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC"
        )
    
    def load_latest(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """查询股票的最新K线"""
        return self.load_one("id = %s", (stock_id,), order_by="date DESC")
    
    def load_by_date(self, date: str) -> List[Dict[str, Any]]:
        """查询指定日期的所有股票K线"""
        return self.load("date = %s", (date,))
    
    def save_klines(self, klines: List[Dict[str, Any]]) -> int:
        """批量保存K线（自动去重）"""
        return self.replace(klines, unique_keys=['id', 'date'])

    def load_first_kline_records(self, stock_ids: Optional[List[str]] = None, threshold: int = 100) -> List[Dict[str, Any]]:
        """
        查询每只股票的第一根K线记录
        
        行为策略：
        - 如果 stock_ids 为空或 None：对全表执行一次性分组查询（用于初始化/空表场景）
        - 如果 stock_ids 数量 <= threshold：逐个股票查询 MIN(date)，逻辑简单，适合小批量
        - 如果 stock_ids 数量 > threshold：使用一次带 IN 子句的分组查询，减少 IO
        """
        # 全量模式：用于初始化或特殊场景
        if not stock_ids or len(stock_ids) > threshold:
            return self.load_first_records(date_field='date', primary_keys=['id', 'date'])
        
        # 小批量：使用 IN + 子查询，一次 IO 完成
        placeholders = ','.join(['%s'] * len(stock_ids))
        query = f"""
            SELECT t1.*
            FROM {self.table_name} t1
            INNER JOIN (
                SELECT id, MIN(date) AS min_date
                FROM {self.table_name}
                WHERE id IN ({placeholders})
                GROUP BY id
            ) t2
            ON t1.id = t2.id
            AND t1.date = t2.min_date
        """
        return self.execute_raw_query(query, tuple(stock_ids))

