"""
行业资金流 Model
"""
from typing import List, Dict, Any, Optional
from utils.db.db_model import BaseTableModel


class IndustryCapitalFlowModel(BaseTableModel):
    """行业资金流 Model"""
    
    def __init__(self, db=None):
        super().__init__('industry_capital_flow', db)
    
    def load_by_date(self, date: str) -> List[Dict[str, Any]]:
        """查询指定日期的所有行业资金流"""
        return self.load("trade_date = %s", (date,))
    
    def load_by_industry(self, industry: str) -> List[Dict[str, Any]]:
        """查询指定行业的资金流历史"""
        return self.load("industry = %s", (industry,), order_by="trade_date DESC")
    
    def load_by_date_range(
        self, 
        industry: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定行业指定日期范围的资金流"""
        return self.load(
            "industry = %s AND trade_date BETWEEN %s AND %s",
            (industry, start_date, end_date),
            order_by="trade_date ASC"
        )
    
    def save_capital_flow(self, flow_data: List[Dict[str, Any]]) -> int:
        """批量保存资金流数据（自动去重）"""
        return self.replace(flow_data, unique_keys=['industry', 'trade_date'])

