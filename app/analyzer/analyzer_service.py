from datetime import datetime
from enum import Enum

class InvestmentResult(Enum):
    WIN = 'win'
    LOSS = 'loss'
    OPEN = 'open'


class AnalyzerService:
    def __init__(self):
        pass

    def get_duration_in_days(self, start_date: str, end_date: str) -> int:
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        return (end - start).days
    
    def get_annual_return(self, profit_rate: float, duration_in_days: int) -> float:
        """
        计算年化收益率
        
        Args:
            profit_rate: 总收益率（小数形式，如0.1表示10%）
            duration_in_days: 投资天数
            
        Returns:
            float: 年化收益率（百分比形式）
        """
        if duration_in_days <= 0:
            return 0.0
        
        # 年化收益率 = (1 + 总收益率)^(365/投资天数) - 1
        annual_return = ((1 + profit_rate) ** (365 / duration_in_days) - 1)
        return annual_return