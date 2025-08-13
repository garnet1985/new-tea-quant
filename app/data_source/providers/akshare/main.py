import datetime
from app.data_source.data_source_service import DataSourceService
from app.data_source.providers.akshare.akshare_API_mod import AkshareAPIModified
from app.data_source.providers.akshare.main_service import AKShareService
from app.data_source.providers.akshare.main_storage import AKShareStorage
from app.data_source.providers.conf.conf import data_default_start_date
from app.data_source.providers.tushare.main import Tushare
from utils.worker import FuturesWorker
from loguru import logger
from typing import List, Dict, Optional
import pandas as pd
import time
from datetime import datetime

class AKShare:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.storage = AKShareStorage(connected_db)
        self.service = AKShareService(is_verbose)
        self.is_verbose = is_verbose
        self.tu = None
        self.api_modified = AkshareAPIModified(is_verbose)
        
        self.max_workers = 2                # 降低到2个线程，减少并发压力
        
        # 添加线程锁，确保多线程环境下的限流安全
        import threading
        # create a locker
        self.api_rate_limit_locker = threading.Lock()

        self.total_jobs = 0
        self.job_complete_counter = 0
        self.latest_market_open_day = None

    def inject_dependency(self, tu: Tushare):
        self.tu = tu
        return self

    def reset_state(self):
        self.total_jobs = 0
        self.job_complete_counter = 0
        self.latest_market_open_day = None
    
    def renew_stock_k_line_factors(self, latest_market_open_day: str, stock_index: list = None):

        self.latest_market_open_day = latest_market_open_day

        jobs = self.get_renewable_stocks(stock_index)

        self.total_jobs = len(jobs)
        start_time = time.time()

        worker = FuturesWorker(max_workers=self.max_workers, is_verbose=False)
        worker.set_job_executor(self.renew_adj_factors_for_single_stock)
        worker.run_jobs(jobs)

        self.reset_state()
        logger.info(f"💾 复权因子更新完成. 耗时: {time.time() - start_time} 秒")

        self.storage.backup_csv_if_needed()


    def get_renewable_stocks(self, stock_index: list = None) -> List[Dict]:
        factor_last_update_dates = self.storage.get_all_stocks_latest_update_dates()

        if len(factor_last_update_dates) == 0:
            logger.info(f"复权因子数据表为空, 需要从CSV文件中导入基础数据. 数据导入中...")
            start_time = time.time()
            self.storage.adj_factor_table.import_from_csv()
            logger.info(f"从CSV文件中导入基础数据完成. 耗时: {time.time() - start_time} 秒")
            return self.get_renewable_stocks(stock_index)
        
        jobs = self.service.get_stocks_needing_update_from_db(factor_last_update_dates)
        jobs += self.service.get_stocks_needing_update_from_stock_index(factor_last_update_dates, stock_index)

        return jobs


    def renew_adj_factors_for_single_stock(self, job_data: Dict) -> None:
        ts_code = job_data['id']
        start_date = job_data['last_update']
        latest_market_open_day = self.latest_market_open_day
        
        tu_factors = self.tu.api.adj_factor(ts_code=ts_code, start_date=start_date, end_date=latest_market_open_day)
        factor_changed_dates = self.service.get_factor_changing_dates(tu_factors)

        if len(factor_changed_dates) > 0:
            factors, is_abort = self.generate_factors(job_data)
            if is_abort:
                return
            self.storage.save_factors(factors)
            logger.info(f"💾 {ts_code} 所有复权因子重新计算完成. total progress: {self.job_complete_counter + 1}/{self.total_jobs} ({((self.job_complete_counter + 1) / self.total_jobs * 100):.1f}%)")
        else:
            if job_data['is_in_db']:
                self.storage.update_factor_last_update_date(ts_code)
                logger.info(f"💾 {ts_code} 没有检查到新的复权因子，更新所有复权因子最后更新时间 total progress: {self.job_complete_counter + 1}/{self.total_jobs} ({((self.job_complete_counter + 1) / self.total_jobs * 100):.1f}%)")
            else:
                self.storage.fake_a_factor_record(ts_code)
                logger.info(f"💾 {ts_code} 数据库里暂时没有当前复权因子的记录，存入一个初始复权因子. total progress: {self.job_complete_counter + 1}/{self.total_jobs} ({((self.job_complete_counter + 1) / self.total_jobs * 100):.1f}%)")
        
        # 在方法结束时增加计数器
        self.job_complete_counter += 1

    def generate_factors(self, job_data: Dict):

        is_abort = False

        ts_code = job_data['id']
        latest_market_open_day = self.latest_market_open_day

        tu_factors = self.tu.api.adj_factor(ts_code=ts_code, start_date=data_default_start_date, end_date=latest_market_open_day)
        qfq_k_lines = self.api_modified.get_k_lines(stock_id=ts_code, start_date=data_default_start_date, end_date=latest_market_open_day)

        if qfq_k_lines is None or qfq_k_lines.empty:
            is_abort = True
            return [], is_abort

        all_factor_changed_dates = self.service.get_factor_changing_dates(tu_factors)
        factors = self.calc_factors(all_factor_changed_dates, job_data, qfq_k_lines)

        return factors, is_abort


    def calc_factors(self, dates: List[str], job_data: Dict, qfq_k_lines: pd.DataFrame):
        raw_close_prices = self.storage.get_close_prices(job_data['id'], dates)
        results = []

        if not raw_close_prices:  # 检查列表是否为空
            return []
            
        for date in dates:
            # 在raw_close_prices列表中查找对应日期的收盘价
            matching_raw = None
            for price_data in raw_close_prices:
                if price_data['date'] == date:
                    matching_raw = price_data
                    break
            
            # 检查是否找到了原始收盘价数据
            if not matching_raw:
                continue
            
            raw_close_price = float(matching_raw['close'])
            
            # 在qfq_k_lines中查找对应日期的收盘价
            qfq_date = DataSourceService.to_hyphen_date_type(date)
            qfq_k_line = qfq_k_lines[qfq_k_lines['日期'] == qfq_date]
            
            # 检查是否找到了前复权K线数据
            if qfq_k_line.empty:
                continue
            
            qfq_close_price = float(qfq_k_line.iloc[0]['收盘'])

            qfq_factor = qfq_close_price / raw_close_price

            results.append({
                'id': job_data['id'],
                'date': date,
                'qfq': qfq_factor,           # 直接使用数据库列名
                'hfq': 0,                     # 直接使用数据库列名
                'last_update': datetime.now() # 直接添加时间戳
            })

        return results