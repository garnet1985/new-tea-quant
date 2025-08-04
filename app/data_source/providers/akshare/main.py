from app.data_source.data_source_service import DataSourceService
from app.data_source.providers.akshare.main_service import AKShareService
from app.data_source.providers.akshare.main_storage import AKShareStorage
from app.data_source.providers.conf.conf import data_default_start_date
from app.data_source.providers.tushare.main import Tushare
from utils.worker import FuturesWorker
from loguru import logger
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from akshare import stock_zh_a_hist
import pandas as pd

class AKShare:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.storage = AKShareStorage(connected_db)
        self.service = AKShareService(is_verbose)
        self.is_verbose = is_verbose
        self.tu = None;
        self.api = stock_zh_a_hist

    def inject_dependency(self, tu: Tushare):
        self.tu = tu
        return self

    def renew_stock_K_line_factors(self, latest_market_open_day: str, stock_index: list = None, force_update = False):
        force_update = True
        if self.is_verbose:
            logger.info(f"Starting stock K-line factors renewal for {len(stock_index) if stock_index else 'all'} stocks")
        
        if not force_update and not self.storage.should_update_adj_factors():
            if self.is_verbose:
                logger.info("factor is up to date, skip.")
            return False
        
        return self.update_adj_factors_by_batch(stock_index, latest_market_open_day)

    def update_adj_factors_by_batch(self, stock_index: list, latest_market_open_day: str) -> bool:
        jobs = self.build_jobs(stock_index, latest_market_open_day)
        return self.execute_jobs(jobs)

    def build_jobs(self, stock_index: list, latest_market_open_day: str) -> List[Dict]:
        jobs = []
        for stock_info in stock_index:
            # 构造ts_code
            ts_code = f"{stock_info['code']}.{stock_info['market']}"
            jobs.append({
                'id': f'fetch_{ts_code}_adjust_factors',
                'data': {
                    'code': stock_info['code'],
                    'ts_code': ts_code,
                    'name': stock_info['name'],
                    'latest_market_open_day': latest_market_open_day
                }
            })
        return jobs

    def execute_jobs(self, jobs: List[Dict]) -> bool:
        worker = FuturesWorker(max_workers=2, is_verbose=self.is_verbose)
        worker.set_job_executor(self.renew_adj_factors_for_single_stock)
        return worker.run_jobs(jobs)

    def renew_adj_factors_for_single_stock(self, job_data: Dict) -> None:
        latest_market_open_day = job_data['latest_market_open_day']

        latest_factor_in_db = self.storage.get_latest_factor(job_data['ts_code'])

        if latest_factor_in_db is None:
            db_latest_factor_change_date = data_default_start_date
        else:
            db_latest_factor_change_date = latest_factor_in_db['date']

        factors_events = self.tu.api.adj_factor(ts_code=job_data['ts_code'], start_date=db_latest_factor_change_date, end_date=latest_market_open_day)
        factor_changing_dates = self.service.get_factor_changing_dates(factors_events)
        qfq_k_lines = self.api(symbol=job_data['code'], period="daily", start_date=db_latest_factor_change_date, end_date=latest_market_open_day, adjust="qfq")
        dates_need_to_renew = self.service.get_renew_dates(db_latest_factor_change_date, factor_changing_dates)
        self.renew_factors(dates_need_to_renew, qfq_k_lines, job_data)


    def renew_factors(self, dates: List[str], qfq_k_lines: pd.DataFrame, job_data: Dict):
        factors = []
        for date in dates:
            factor = self.calc_factors(date, job_data, qfq_k_lines)
            if factor:
                factors.append(factor)

        # 转换为存储格式
        if factors:
            factors_data = []
            for factor in factors:
                factors_data.append((
                    job_data['ts_code'],  # ts_code
                    factor['date'],       # date
                    factor['qfq_factor'], # qfq_factor
                    factor['hfq_factor']  # hfq_factor
                ))
            self.storage.batch_upsert_adj_factors(factors_data)
        
        return factors
    
    def calc_factors(self, date: str, job_data: Dict, qfq_data: pd.DataFrame) -> Optional[Dict]:
        # 从数据库获取不复权收盘价
        raw_close = self.storage.get_close_price(job_data['ts_code'], date)

        if raw_close is None or qfq_data.empty:
            return None

        # 将日期格式从 YYYYMMDD 转换为 datetime.date 对象
        date_formatted = DataSourceService.to_hyphen_date_type(date)
        
        # 在DataFrame中查找对应日期的收盘价
        matching_rows = qfq_data[qfq_data['日期'] == date_formatted]
        
        if matching_rows.empty:
            return None
            
        qfq_close = float(matching_rows.iloc[0]['收盘'])
        qfq_factor = qfq_close / raw_close

        # todo: add hfq_factor later, now set it default to 0 means data is not available
        return {
            'date': date,
            'qfq_factor': qfq_factor,
            'hfq_factor': 0  # 后复权因子设为0，因为我们不计算它
        }
