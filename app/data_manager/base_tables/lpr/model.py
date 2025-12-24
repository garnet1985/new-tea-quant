"""
LPR利率 Model
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel

class LprModel(DbBaseModel):
    """LPR利率 Model"""
    
    def __init__(self, db=None):
        super().__init__('lpr', db)
    
    def load_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """查询指定日期的LPR利率（带回退）"""
        return self.load_one("date <= %s", (date,), order_by="date DESC")
    
    def load_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的LPR利率"""
        return self.load(
            "date BETWEEN %s AND %s",
            (start_date, end_date),
            order_by="date ASC"
        )
    
    def load_latest(self) -> Optional[Dict[str, Any]]:
        """查询最新的LPR利率"""
        return self.load_one("1=1", order_by="date DESC")
    
    def save_lpr_data(self, lpr_data: List[Dict[str, Any]]) -> int:
        """批量保存LPR数据（自动去重）"""
        return self.replace(lpr_data, unique_keys=['date'])

