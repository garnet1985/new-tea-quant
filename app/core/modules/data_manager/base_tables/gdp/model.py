"""
GDP数据 Model
"""
from typing import List, Dict, Any, Optional
from app.core.infra.db import DbBaseModel


class GdpModel(DbBaseModel):
    """GDP数据 Model"""
    
    def __init__(self, db=None):
        super().__init__('gdp', db)
    
    def load_by_quarter(self, quarter: str) -> Optional[Dict[str, Any]]:
        """查询指定季度的GDP数据"""
        return self.load_one("quarter = %s", (quarter,))
    
    def load_by_date_range(
        self, 
        start_quarter: str, 
        end_quarter: str
    ) -> List[Dict[str, Any]]:
        """查询指定季度范围的GDP数据"""
        return self.load(
            "quarter BETWEEN %s AND %s",
            (start_quarter, end_quarter),
            order_by="quarter ASC"
        )
    
    def load_latest(self) -> Optional[Dict[str, Any]]:
        """查询最新的GDP数据"""
        return self.load_one("1=1", order_by="quarter DESC")
    
    def save_gdp_data(self, gdp_data: List[Dict[str, Any]]) -> int:
        """批量保存GDP数据（自动去重）"""
        return self.replace(gdp_data, unique_keys=['quarter'])

