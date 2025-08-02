from app.data_source.providers.akshare.main_settings import factor_update_interval_days
from loguru import logger
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class AKShareStorage:
    def __init__(self, connected_db):
        self.meta_info_table = connected_db.get_table_instance('meta_info')
        self.adj_factor_table = connected_db.get_table_instance('adj_factor')

    def batch_upsert_adj_factors(self, factors_data: List[Tuple]) -> bool:
        # 先删除该股票的所有旧因子记录
        for stock_code, market, _, _, _ in factors_data:
            self.adj_factor_table.delete_adj_factor(stock_code, market, '20080101')
        
        # 插入新的因子记录
        return self.adj_factor_table.batch_upsert_adj_factors(factors_data)

    def get_adj_factor(self, code: str, market: str, trade_date: str) -> Optional[Dict]:
        return self.adj_factor_table.get_adj_factor(code, market, trade_date)

    def get_adj_factors_by_date_range(self, code: str, market: str, start_date: str, end_date: str) -> List[Dict]:
        return self.adj_factor_table.get_adj_factors_by_date_range(code, market, start_date, end_date)

    def get_latest_adj_factor(self, code: str, market: str) -> Optional[Dict]:
        return self.adj_factor_table.get_latest_adj_factor(code, market)

    def has_factor_changes(self, code: str, market: str, since_date: str) -> bool:
        return self.adj_factor_table.has_factor_changes(code, market, since_date)

    def should_update_adj_factors(self, days_threshold: int = factor_update_interval_days) -> bool:
        last_update_str = self.meta_info_table.get_meta_info_by_key('akshare_adj_factors_last_update')
        
        if not last_update_str:
            logger.info("没有找到上次更新时间记录，需要更新")
            return True
        
        last_update = datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
        current_time = datetime.now()
        time_diff = current_time - last_update
        
        if time_diff.days >= days_threshold:
            logger.info(f"距离上次更新已过去 {time_diff.days} 天，需要更新")
            return True
        else:
            logger.info(f"距离上次更新仅过去 {time_diff.days} 天，无需更新")
            return False

    def update_last_update_time(self):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.meta_info_table.set_meta_info_by_key('akshare_adj_factors_last_update', current_time)
        logger.info(f"更新复权因子最后更新时间: {current_time}")

    def get_update_status_info(self) -> Dict:
        last_update_str = self.meta_info_table.get_meta_info_by_key('akshare_adj_factors_last_update')
        
        if not last_update_str:
            return {
                'last_update': None,
                'days_since_update': None,
                'needs_update': True,
                'status': 'never_updated'
            }
        
        last_update = datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
        current_time = datetime.now()
        days_since_update = (current_time - last_update).days
        
        return {
            'last_update': last_update_str,
            'days_since_update': days_since_update,
            'needs_update': days_since_update >= factor_update_interval_days,
            'status': 'up_to_date' if days_since_update < factor_update_interval_days else 'needs_update'
        }
