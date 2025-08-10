from app.data_source.providers.akshare.main_settings import factor_update_interval_days
from loguru import logger
from datetime import datetime
from typing import Dict, Optional
from app.data_source.data_source_service import DataSourceService

class AKShareStorage:
    def __init__(self, connected_db):
        self.meta_info_table = connected_db.get_table_instance('meta_info')
        self.adj_factor_table = connected_db.get_table_instance('adj_factor')
        self.stock_kline_table = connected_db.get_table_instance('stock_kline')

    def batch_upsert_adj_factors(self, factors_data) -> bool:        
        # 插入新的因子记录
        return self.adj_factor_table.batch_upsert_adj_factors(factors_data)

    def get_latest_factor_change_date(self) -> str:
        last_update_str = self.meta_info_table.get_meta_info_by_key('akshare_adj_factors_last_update')
        if not last_update_str:
            return None
        return last_update_str

    def should_update_adj_factors(self):
        info = ""
        should_update = False
        last_update_str = self.get_latest_factor_change_date()

        if not last_update_str:
            should_update = True
            info = "没有任何复权因子的更新记录，需要更新"
            return should_update, info
        
        last_update = datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
        current_time = datetime.now()
        time_diff = current_time - last_update
        
        if time_diff.days > factor_update_interval_days:
            should_update = True
            info = f"复权因子距离上次更新已超过强制期限（{factor_update_interval_days}天），需要更新"
            return should_update, info
        else:
            info = f"距离上次更新仅过去 {time_diff.days} 天小于强制更新期限（{factor_update_interval_days}天），是否更新? y:更新 | 其他任意键:不更新"
            should_update = False
            return should_update, info

    def update_last_update_time(self):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.meta_info_table.set_meta_info_by_key('akshare_adj_factors_last_update', current_time)

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
    
    def get_close_price(self, ts_code: str, trade_date: str) -> Optional[float]:
        code, market = DataSourceService.parse_ts_code(ts_code)
        result = self.stock_kline_table.get_by_date(code, market, trade_date)
        if result:
            return float(result[0]['close'])
        else:
            return None

    def get_latest_factor(self, ts_code: str) -> Optional[Dict]:
        return self.adj_factor_table.get_latest_factor(ts_code)

