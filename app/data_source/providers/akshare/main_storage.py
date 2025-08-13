import pandas as pd
from app.data_source.providers.akshare.main_settings import factor_update_interval_days
from loguru import logger
from datetime import datetime
from typing import Dict, List, Optional
from app.data_source.data_source_service import DataSourceService

class AKShareStorage:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.adj_factor_table = connected_db.get_table_instance('adj_factor')
        self.stock_kline_table = connected_db.get_table_instance('stock_kline')
        self.is_verbose = is_verbose
        self.db = connected_db

    def get_all_stocks_latest_update_dates(self) -> list:   
        return self.adj_factor_table.get_all_stocks_latest_update_dates()

    def update_factor_last_update_date(self, ts_code: str) -> None:
        """更新指定股票代码的所有复权因子的last_update时间为当前时间"""
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        # 更新该股票所有复权因子的last_update时间
        self.adj_factor_table.update(
            data={'last_update': now_str},
            condition="id = %s",
            params=(ts_code,)
        )

    def fake_a_factor_record(self, ts_code: str) -> None:
        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        today = now.strftime('%Y%m%d')  # 使用 YYYYMMDD 格式匹配数据库
        self.adj_factor_table.insert([
            {
                'id': ts_code, 
                'date': today, 
                'qfq': 1, 
                'hfq': 0, 
                'last_update': now_str
            }
        ])


    def get_adj_factor_for_date(self, ts_code: str, target_date: str) -> Optional[Dict]:
        """
        获取指定日期的复权因子
        如果目标日期不是复权事件日期，返回最近的前一个复权事件日期的因子
        """
        all_factors = self.get_all_adj_factors(ts_code)
        if not all_factors:
            return None
        
        # 找到小于等于目标日期的最近复权事件日期
        applicable_factors = []
        for factor in all_factors:
            if factor['date'] <= target_date:
                applicable_factors.append(factor)
        
        if applicable_factors:
            # 返回最新的适用因子
            return max(applicable_factors, key=lambda x: x['date'])
        
        return None
    
    def get_close_prices(self, ts_code: str, trade_dates: List[str]) -> List[Dict]:
        result = self.stock_kline_table.get_by_dates(ts_code, trade_dates)
        if result:
            return result
        else:
            return []
    
    def save_factors(self, factors: List[Dict]) -> None:
        if not factors or len(factors) == 0:
            return
        
        ts_code = factors[0]['id']
        
        # 先删除该股票的所有复权因子
        self.adj_factor_table.delete("id = %s", (ts_code,))
        # 使用 insert 方法批量插入
        self.adj_factor_table.insert(factors)


