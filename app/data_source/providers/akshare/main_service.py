import pandas as pd
from datetime import datetime
from typing import Dict, List
from loguru import logger


from app.data_source.providers.akshare.main_settings import factor_update_interval_days
from app.conf.conf import data_default_start_date


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
            
            # 只有当因子真正发生变化时才记录日期
            if prev_factor is not None and current_factor != prev_factor:
                changing_dates.append(trade_date)
            
            prev_factor = current_factor
        
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

    def get_stocks_needing_update_from_db(self, factor_last_update_dates: list) -> List[Dict]:
        # 找到最新的日期
        results = []
        current_date = datetime.now()
        for stock in factor_last_update_dates:
            if not stock['last_update'] or (current_date - stock['last_update']).days > factor_update_interval_days:
                results.append(self.to_job_data(stock['id'], stock['last_update'], True))

        return results


    def get_stocks_needing_update_from_stock_list(self, db_stocks: list, stock_list: list) -> List[Dict]:
        # 创建数据库中已有股票的代码集合
        db_stock_codes = set(stock.get('id') for stock in db_stocks)
        
        # 找出在stock_list中存在但在数据库中没有存储过的股票
        missing_in_db = []
        for stock in stock_list:
            stock_id = stock.get('id')
            if stock_id and stock_id not in db_stock_codes:
                missing_in_db.append(self.to_job_data(stock_id, None, False))
            
        return missing_in_db


    def to_job_data(self, stock_id: str, last_update: datetime, is_in_db: bool) -> Dict:
        # 处理start_date格式
        start_date = last_update
        if hasattr(start_date, 'strftime'):
            start_date = start_date.strftime('%Y%m%d')
        elif start_date is None:
            start_date = data_default_start_date
        
        return {
            'id': f"fetch_{stock_id}_adjust_factors",
            'data': {
                'id': stock_id,
                'last_update': start_date,  # 已经是字符串格式
                'is_in_db': is_in_db
            },
        }