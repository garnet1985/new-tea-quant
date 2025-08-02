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
            
            hfq_data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="hfq"
            )
            
            if raw_data.empty or hfq_data.empty:
                return None
            
            merged_data = pd.merge(raw_data, hfq_data, on='日期', suffixes=('_raw', '_hfq'))
            merged_data['hfq_factor'] = merged_data['收盘_hfq'] / merged_data['收盘_raw']
            merged_data['qfq_factor'] = 1.0
            
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

    def prepare_factor_data(self, merged_data: pd.DataFrame, stock_code: str, market: str) -> List[Tuple]:
        factors_data = []
        
        # 只取最新的因子数据，使用一个很早的日期作为通用因子
        latest_data = merged_data.iloc[-1]
        universal_date = '20080101'  # 使用一个很早的日期，这样查询任意日期都能找到
        
        factors_data.append((
            stock_code,
            market,
            universal_date,
            float(latest_data['qfq_factor']),
            float(latest_data['hfq_factor'])
        ))
        
        return factors_data

    def get_today_date(self) -> str:
        return datetime.now().strftime('%Y%m%d')
    
    def get_recent_date_range(self, days: int = 5) -> Tuple[str, str]:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        return start_date, end_date
