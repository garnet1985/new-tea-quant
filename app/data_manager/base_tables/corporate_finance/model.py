"""
公司财务数据 Model
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel


class CorporateFinanceModel(DbBaseModel):
    """公司财务数据 Model"""
    
    def __init__(self, db=None):
        super().__init__('corporate_finance', db)
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有财务数据"""
        return self.load("id = %s", (stock_id,), order_by="end_date DESC")
    
    def load_by_quarter(
        self, 
        stock_id: str, 
        end_date: str
    ) -> Optional[Dict[str, Any]]:
        """查询指定股票指定季度的财务数据"""
        return self.load_one("id = %s AND end_date = %s", (stock_id, end_date))
    
    def load_latest_by_stock(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """查询股票的最新财务数据"""
        return self.load_one("id = %s", (stock_id,), order_by="end_date DESC")
    
    def load_by_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的财务数据"""
        return self.load(
            "id = %s AND end_date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="end_date ASC"
        )
    
    def save_finance_data(self, finance_data: List[Dict[str, Any]]) -> int:
        """批量保存财务数据（自动去重）"""
        return self.replace(finance_data, unique_keys=['id', 'end_date'])

