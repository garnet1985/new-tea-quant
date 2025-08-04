import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from loguru import logger

from app.data_source.providers.conf.conf import data_default_start_date

class AKShareService:
    def __init__(self, is_verbose: bool = False):
        self.is_verbose = is_verbose

    def fetch_stock_factors(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        # 分批获取数据，避免单次请求时间跨度过长
        all_data = []
        current_start = start_date
        
        while current_start <= end_date:
            # 计算当前批次的结束日期（最多1年）
            current_end = self._calculate_batch_end_date(current_start, end_date)
            
            if self.is_verbose:
                logger.info(f"Fetching {stock_code} data from {current_start} to {current_end}")
            
            batch_data = self._fetch_single_batch(stock_code, current_start, current_end)
            if batch_data is not None and not batch_data.empty:
                all_data.append(batch_data)
            
            # 移动到下一批次
            current_start = self._get_next_batch_start(current_end)
        
        if not all_data:
            return None
        
        # 合并所有批次的数据
        merged_data = pd.concat(all_data, ignore_index=True)
        merged_data = merged_data.drop_duplicates(subset=['日期']).sort_values('日期')
        
        return merged_data[['日期', 'qfq_factor', 'hfq_factor']]
    
    def _fetch_single_batch(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        try:
            raw_data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )
            
            qfq_data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            hfq_data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="hfq"
            )
            
            if raw_data.empty or qfq_data.empty or hfq_data.empty:
                return None
            
            # 合并原始数据和前复权数据
            merged_data = pd.merge(raw_data, qfq_data, on='日期', suffixes=('_raw', '_qfq'))
            # 再合并后复权数据
            merged_data = pd.merge(merged_data, hfq_data, on='日期', suffixes=('', '_hfq'))
            
            # 计算复权因子
            merged_data['qfq_factor'] = merged_data['收盘_qfq'] / merged_data['收盘_raw']
            merged_data['hfq_factor'] = merged_data['收盘'] / merged_data['收盘_raw']
            
            return merged_data[['日期', 'qfq_factor', 'hfq_factor']]
        except Exception as e:
            if self.is_verbose:
                logger.error(f"Failed to fetch batch data for {stock_code} from {start_date} to {end_date}: {e}")
            return None
    
    def _calculate_batch_end_date(self, start_date: str, max_end_date: str) -> str:
        # 计算当前批次的结束日期，最多1年
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        max_end_dt = datetime.strptime(max_end_date, '%Y%m%d')
        
        # 计算1年后的日期
        one_year_later = start_dt.replace(year=start_dt.year + 1)
        
        # 返回较早的日期
        batch_end_dt = min(one_year_later, max_end_dt)
        return batch_end_dt.strftime('%Y%m%d')
    
    def _get_next_batch_start(self, current_end_date: str) -> str:
        # 获取下一批次的开始日期（当前结束日期的下一天）
        current_end_dt = datetime.strptime(current_end_date, '%Y%m%d')
        next_start_dt = current_end_dt + timedelta(days=1)
        return next_start_dt.strftime('%Y%m%d')


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