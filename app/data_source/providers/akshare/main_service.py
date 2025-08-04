import pandas as pd
from typing import List
from loguru import logger

class AKShareService:
    def __init__(self, is_verbose: bool = False):
        self.is_verbose = is_verbose

    def get_factor_changing_dates(self, factors_df) -> List[str]:
        if factors_df is None or factors_df.empty:
            return []
        
        # 按日期排序，确保从新到旧
        # the order must be ascending from old date to new date, otherwise the result will be wrong
        factors_df = factors_df.sort_values('trade_date', ascending=True)
        
        # 提取复权因子发生变化的日期
        changing_dates = []
        prev_factor = None
        
        for _, row in factors_df.iterrows():
            current_factor = float(row['adj_factor'])
            trade_date = str(row['trade_date'])
            date_str = trade_date.replace('-', '')
            
            # 如果因子发生变化，记录这个日期
            if prev_factor is not None and current_factor != prev_factor:
                changing_dates.append(date_str)
            
            prev_factor = current_factor
        
        # 反转列表，使其按时间顺序排列
        changing_dates.reverse()
        
        return changing_dates

    def get_renew_dates(self, db_latest_factor_change_date: str, factor_changing_dates: List[str]) -> List[str]:
        if factor_changing_dates is None or len(factor_changing_dates) == 0:
            return []
        
        # 过滤出在数据库最新日期之后的因子变化日期
        renew_dates = []
        for date in factor_changing_dates:
            if date > db_latest_factor_change_date:
                renew_dates.append(date)
        
        return renew_dates