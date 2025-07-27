from datetime import datetime, timedelta
import tushare as ts
from loguru import logger
from app.data_source.providers.tushare.settings import (
    auth_token
)
from app.data_source.providers.conf.conf import data_default_start_date, kline_terms
from app.data_source.providers.tushare.storage import TushareStorage

class Tushare:
    def __init__(self, connected_db):
        self.db = connected_db
        self.storage = TushareStorage(connected_db)

        self.meta_info = self.db.get_table_instance('meta_info', 'base')

        self.token = self.get_token()
        ts.set_token(self.token)

        self.pro = ts.pro_api()

        self.last_market_open_day = None

    def renew_data(self):
        self.last_market_open_day = self.get_last_market_open_day()
        if self.last_market_open_day != None:
            self.renew_stock_index()
            self.renew_stock_kline_by_batch()
        else:
            logger.error("无法获取交易日历, renew job 失败!")





    

    def generate_kline_renew_jobs(self, stock_idx_info: list) -> list:
        jobs = []
        current_data = self.storage.get_all_latest_kline_dates()
        
        for code, market in stock_idx_info:
            jobs += self.to_single_stock_kline_renew_job({
                'ts_code': self.to_storage_code(code, market),
                'code': code,
                'market': market
            }, current_data)

        return jobs


    def to_single_stock_kline_renew_job(self, stock_idx_info: dict, current_data: dict) -> dict:
        jobs = []
        for term in kline_terms:
            job = self.to_single_stock_kline_renew_job_by_term(term, stock_idx_info, current_data)
            if job:
                jobs.append(job)
        return jobs


    def to_single_stock_kline_renew_job_by_term(self, term: str, stock_idx_info: dict, current_data: dict) -> dict:
        # 获取该股票该周期的最新数据日期
        latest_date = current_data.get(stock_idx_info['ts_code'], {}).get(term)

        if not latest_date:
            # 没有数据，使用默认开始日期
            return {
                'code': stock_idx_info['code'],
                'market': stock_idx_info['market'],
                'ts_code': stock_idx_info['ts_code'],
                'term': term,
                'start_date': data_default_start_date,
                'end_date': self.last_market_open_day
            }
        
        latest_dt = datetime.strptime(latest_date, '%Y%m%d')
        last_market_dt = datetime.strptime(self.last_market_open_day, '%Y%m%d')

        if term == 'daily':
            if latest_dt < last_market_dt:
                start_date = (latest_dt + timedelta(days=1)).strftime('%Y%m%d')
                return {
                    'code': stock_idx_info['code'],
                    'market': stock_idx_info['market'],
                    'ts_code': stock_idx_info['ts_code'],
                    'term': term,
                    'start_date': start_date,
                    'end_date': self.last_market_open_day
                }
            else:
                return None
        
        elif term == 'weekly':
            latest_week_start = latest_dt - timedelta(days=latest_dt.weekday())
            last_market_week_start = last_market_dt - timedelta(days=last_market_dt.weekday())
            
            if latest_week_start < last_market_week_start:
                # 需要更新：从最新周的下一个周开始
                next_week_start = latest_week_start + timedelta(days=7)
                start_date = next_week_start.strftime('%Y%m%d')
                return {
                    'code': stock_idx_info['code'],
                    'market': stock_idx_info['market'],
                    'ts_code': stock_idx_info['ts_code'],
                    'term': term,
                    'start_date': start_date,
                    'end_date': self.last_market_open_day,
                    'reason': 'weekly_update'
                }
                
        elif term == 'monthly':
            # 月线：检查是否包含最新的完整月
            latest_month_start = latest_dt.replace(day=1)
            last_market_month_start = last_market_dt.replace(day=1)
            
            if latest_month_start < last_market_month_start:
                # 需要更新：从最新月的下一个月开始
                if latest_month_start.month == 12:
                    next_month_start = latest_month_start.replace(year=latest_month_start.year + 1, month=1)
                else:
                    next_month_start = latest_month_start.replace(month=latest_month_start.month + 1)
                start_date = next_month_start.strftime('%Y%m%d')
                return {
                    'code': stock_idx_info['code'],
                    'market': stock_idx_info['market'],
                    'ts_code': stock_idx_info['ts_code'],
                    'term': term,
                    'start_date': start_date,
                    'end_date': self.last_market_open_day,
                    'reason': 'monthly_update'
                }
        
        # 不需要更新
        return None

    def execute_stock_kline_renew_jobs(self, jobs: list, batch_size: int = 10):
        if not jobs:
            logger.info("没有需要更新的K线数据任务")
            return
        
        total_jobs = len(jobs)
        logger.info(f"开始执行 {total_jobs} 个K线数据更新任务")
        
        for i, job in enumerate(jobs):
            try:
                logger.info(f"执行进度: {(i+1)/total_jobs * 100:.1f}% ({i+1}/{total_jobs}) | 细节: {job['ts_code']} {job['term']} ({job['start_date']} -> {job['end_date']})")
                
                # 这里调用具体的K线数据获取和保存逻辑
                data = self.fetch_kline_data(job)
                self.storage.save_stock_kline(data, job)
                # self.fetch_and_save_kline_data(job)
                
                # 每处理一批任务后暂停一下，避免API限制
                if (i + 1) % batch_size == 0:
                    logger.info(f"已处理 {i+1}/{total_jobs} 个任务，暂停1秒...")
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"执行任务失败 {job['code']} {job['term']}: {e}")
                continue
        logger.info(f"K线数据更新任务执行完成，共处理 {total_jobs} 个任务")

    def fetch_kline_data(self, job: dict):
        if job['term'] == 'daily':
            return self.pro.daily(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
        elif job['term'] == 'weekly':
            return self.pro.weekly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
        elif job['term'] == 'monthly':
            return self.pro.monthly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
    

    def renew_stock_kline_by_batch(self):
        """
        批量更新股票K线数据
        """
        # 获取所有股票代码和市场信息
        stock_index_data = self.storage.get_stock_index()
        stock_idx_info = [(stock['code'], stock['market']) for stock in stock_index_data]

        # TODO: remove below slicing
        stock_idx_info = stock_idx_info[:5]
        
        # 生成更新任务
        jobs = self.generate_kline_renew_jobs(stock_idx_info)

        self.execute_stock_kline_renew_jobs(jobs)






    # stock index related
    def renew_stock_index(self, is_force=True):

        if is_force:
            print('renew stock index')
            data = self.request_stock_index()
            self.storage.save_stock_index(data)
            self.meta_info.set_meta_info('stock_index_last_update', self.last_market_open_day)
            return



        meta_info = self.meta_info.get_meta_info('stock_index_last_update')
        if meta_info == None:
            print('renew stock index')
            data = self.request_stock_index()
            self.storage.save_stock_index(data)
            self.meta_info.set_meta_info('stock_index_last_update', self.last_market_open_day)
        else:
            if meta_info < self.last_market_open_day:
                print('renew stock index')
                data = self.request_stock_index()
                self.storage.save_stock_index(data)
                self.meta_info.set_meta_info('stock_index_last_update', self.last_market_open_day)
            else:
                print('stock index is up to date')

    def request_stock_index(self):
        fields = 'ts_code,name,area,industry,market,exchange,list_date'
        stock_status = 'L'
        data = self.pro.stock_basic(exchange='', list_status=stock_status, fields=fields)
        return data



    # # stock kline related
    # def renew_stock_kline(self):
    #     """旧的单股票K线更新方法 (保留兼容性)"""
    #     stock_index = self.storage.get_stock_index()

    #     for idx in stock_index:
    #         if self.storage.should_renew_stock_kline(idx['code'], 'daily', self.last_market_open_day):
    #             self.renew_stock_kline_by_code(idx['code'], 'daily')
    #         else:
    #             print(f"stock kline for {idx['code']} is up to date")

    # def renew_stock_kline_by_code(self, code: str, term: str):
    #     """根据股票代码和周期更新K线数据"""
    #     # TODO: 实现具体的K线数据获取和保存逻辑
    #     logger.info(f"更新K线数据: {code} {term}")




    # auth related
    def get_token(self):
        try:
            with open(auth_token, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Token file not found: {auth_token}. Please create the token file with your Tushare token.")


    # Market open date & calendar related
    def get_last_market_open_day(self):
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        try:
            dates = self.pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
            # 检查返回的字段名
            if 'is_open' in dates.columns:
                last_market_open_day = dates[dates['is_open'] == 1]['cal_date'].max()
            elif 'is_open' in dates.columns:
                last_market_open_day = dates[dates['is_open'] == 1]['cal_date'].max()
            else:
                # 如果字段名不匹配，使用当前日期作为默认值
                logger.warning("无法获取交易日历，使用当前日期作为默认值")
                last_market_open_day = datetime.now().strftime('%Y%m%d')
            return last_market_open_day
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            # 使用当前日期作为默认值
            return datetime.now().strftime('%Y%m%d')

    
    def to_storage_code(self, code: str, market: str):
        return code + '.' + market