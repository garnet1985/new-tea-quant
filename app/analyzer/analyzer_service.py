from datetime import datetime
from enum import Enum
from .analyzer_settings import conf

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
        if duration_in_days <= 0:
            return 0.0
        
        # 对于短期投资，使用简单的年化公式：年化收益率 = 总收益率 * (365/投资天数)
        # 这样可以避免短期投资产生极其夸张的年化收益率
        annual_return = profit_rate * (365 / duration_in_days)
        return annual_return

    @staticmethod
    def to_usable_stock_idx(stock_idx):
        if not stock_idx:
            return []
            
        filtered_idx = []
        
        for stock in stock_idx:
            stock_id = stock.get('id', '')
            stock_name = stock.get('name', '')
            
            # 过滤条件1：排除北交所股票（ID包含BJ）
            avoid_name_starts_with = conf['stock_idx']['avoid_name_starts_with']
            avoid_code_starts_with = conf['stock_idx']['avoid_code_starts_with']
            avoid_exchange_center = conf['stock_idx']['avoid_exchange_center']

            if any(stock_name.startswith(prefix) for prefix in avoid_name_starts_with):
                continue

            if any(stock_id.startswith(prefix) for prefix in avoid_code_starts_with):
                continue

            if any(string in stock_id for string in avoid_exchange_center):
                continue

            # 通过所有过滤条件，添加到结果列表
            filtered_idx.append(stock)
            
        return filtered_idx