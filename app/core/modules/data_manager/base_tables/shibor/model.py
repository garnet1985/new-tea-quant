"""
Shibor利率 Model
"""
from typing import List, Dict, Any, Optional
from app.core.infra.db import DbBaseModel


class ShiborModel(DbBaseModel):
    """Shibor利率 Model"""
    
    def __init__(self, db=None):
        super().__init__('shibor', db)
    
    def load_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """查询指定日期的Shibor利率（带回退）"""
        return self.load_one("date <= %s", (date,), order_by="date DESC")
    
    def load_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的Shibor利率"""
        return self.load(
            "date BETWEEN %s AND %s",
            (start_date, end_date),
            order_by="date ASC"
        )
    
    def load_latest(self) -> Optional[Dict[str, Any]]:
        """查询最新的Shibor利率"""
        return self.load_one("1=1", order_by="date DESC")
    
    def save_shibor_data(self, shibor_data: List[Dict[str, Any]]) -> int:
        """批量保存Shibor数据（自动去重）"""
        return self.replace(shibor_data, unique_keys=['date'])

