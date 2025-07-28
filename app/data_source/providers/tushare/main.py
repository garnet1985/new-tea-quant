from datetime import datetime, timedelta
import tushare as ts
from loguru import logger
from app.data_source.providers.tushare.settings import (
    auth_token
)
from app.data_source.providers.tushare.main_service import TushareService
from app.data_source.providers.tushare.main_storage import TushareStorage

class Tushare:
    def __init__(self, connected_db):
        self.db = connected_db
        self.storage = TushareStorage(connected_db)
        self.service = TushareService()

        self.latest_market_open_day = None
        self.latest_stock_index = None

        self.use_token();
        self.api = ts.pro_api()


    def renew_data(self):
        self.latest_market_open_day = self.service.get_latest_market_open_day(self.api)
        if self.latest_market_open_day != None:
            self.latest_stock_index = self.renew_stock_index()
            self.renew_stock_kline_by_batch()
        else:
            logger.error("Can not retrieve most recent market open date, renew job blocked!")
    

    def renew_stock_kline_by_batch(self):
        """
        批量更新股票K线数据
        """
        # 获取所有股票代码和市场信息
        stock_idx_info = [(stock['code'], stock['market']) for stock in self.latest_stock_index]

        # TODO: remove below slicing
        stock_idx_info = stock_idx_info[:5]
        
        # 生成更新任务
        jobs = self.service.generate_kline_renew_jobs(stock_idx_info, self.latest_market_open_day, self.storage)

        self.execute_stock_kline_renew_jobs(jobs)



    def execute_stock_kline_renew_jobs(self, jobs: list, batch_size: int = 10):
        if not jobs:
            logger.info("No kline renew jobs")
            return
        
        total_jobs = len(jobs)
        logger.info(f"Start to execute {total_jobs} stock kline renew jobs")
        
        for i, job in enumerate(jobs):
            logger.info(f"Progress: {(i+1)/total_jobs * 100:.1f}% ({i+1}/{total_jobs}) | Detail: {job['ts_code']} {job['term']} ({job['start_date']} -> {job['end_date']})")
            
            # 这里调用具体的K线数据获取和保存逻辑
            data = self.fetch_kline_data(job)
            self.storage.save_stock_kline(data, job)

            continue

        logger.info(f"All {total_jobs} stock kline renew jobs completed")

    def fetch_kline_data(self, job: dict):
        if job['term'] == 'daily':
            return self.api.daily(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
        elif job['term'] == 'weekly':
            return self.api.weekly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
        elif job['term'] == 'monthly':
            return self.api.monthly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])


    # stock index related
    def renew_stock_index(self, is_force=True):

        meta_info_key = 'stock_index_last_update'

        if is_force:
            print('renew stock index')
            idx_data = self.request_stock_index()
            self.storage.save_stock_index(idx_data)
            self.storage.save_meta_info(meta_info_key, self.latest_market_open_day)
            return idx_data

        meta_info = self.storage.get_meta_info(meta_info_key)
        if meta_info == None:
            idx_data = self.request_stock_index()
            self.storage.save_stock_index(idx_data)
            self.storage.save_meta_info(meta_info_key, self.latest_market_open_day)
            return idx_data
        else:
            if meta_info < self.latest_market_open_day:
                idx_data = self.request_stock_index()
                self.storage.save_stock_index(idx_data)
                self.storage.save_meta_info(meta_info_key, self.latest_market_open_day)
                return idx_data
            else:
                logger.info('stock index is up to date, no need to renew')
                return None


    def request_stock_index(self):
        fields = 'ts_code,name,area,industry,market,exchange,list_date'
        stock_status = 'L'
        data = self.api.stock_basic(exchange='', list_status=stock_status, fields=fields)
        return data

    
    def to_storage_code(self, code: str, market: str):
        return code + '.' + market

    # auth related
    def get_token(self):
        try:
            with open(auth_token, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Token file not found: {auth_token}. Please create the token file with your Tushare token.")

    def use_token(self):
        ts.set_token(self.get_token())