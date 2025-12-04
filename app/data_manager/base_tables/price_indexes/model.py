"""
价格指数（CPI/PPI/PMI）Model
"""
from typing import List, Dict, Any, Optional
from utils.db.db_model import BaseTableModel


class PriceIndexesModel(BaseTableModel):
    """价格指数 Model"""
    
    def __init__(self, db=None):
        super().__init__('price_indexes', db)
    
    def load_by_month(self, month: str) -> Optional[Dict[str, Any]]:
        """查询指定月份的价格指数"""
        return self.load_one("month = %s", (month,))
    
    def load_by_date_range(
        self, 
        start_month: str, 
        end_month: str
    ) -> List[Dict[str, Any]]:
        """查询指定月份范围的价格指数"""
        return self.load(
            "month BETWEEN %s AND %s",
            (start_month, end_month),
            order_by="month ASC"
        )
    
    def load_latest(self) -> Optional[Dict[str, Any]]:
        """查询最新的价格指数"""
        return self.load_one("1=1", order_by="month DESC")
    
    def save_price_indexes(self, indexes: List[Dict[str, Any]]) -> int:
        """批量保存价格指数（自动去重）"""
        return self.replace(indexes, unique_keys=['month'])

