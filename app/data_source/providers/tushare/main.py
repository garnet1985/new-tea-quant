from datetime import datetime, timedelta
import tushare as ts
from loguru import logger
from app.data_source.providers.tushare.settings import (
    auth_token
)
from app.data_source.providers.conf.conf import data_start_date
from app.data_source.providers.tushare.storage import TushareStorage

class Tushare:
    def __init__(self, connected_db):
        self.db = connected_db
        self.storage = TushareStorage(connected_db)

        self.meta_info = self.db.get_table_instance('meta_info', 'base')

        self.token = self.get_token()
        ts.set_token(self.token)

        self.pro = ts.pro_api()

        self.last_market_open_day = self.get_last_market_open_day()

    def renew_data(self):
        self.renew_stock_index()
        self.renew_stock_kline_batch()

    def generate_kline_update_jobs(self, stock_info: list, terms: list, 
                                 last_market_open_day: str, default_start_date: str = '20080101') -> list:
        """
        生成K线数据更新任务列表
        
        Args:
            stock_info: 股票信息列表，每个元素为 (code, market) 元组
            terms: 周期列表 ['daily', 'weekly', 'monthly']
            last_market_open_day: 最后交易日
            default_start_date: 默认开始日期（当没有数据时使用）
            
        Returns:
            任务列表，每个任务包含 code, market, ts_code, term, start_date, end_date, reason
        """
        from datetime import datetime, timedelta
        
        jobs = []
        latest_data = self.storage.get_all_latest_kline_data()
        
        for code, market in stock_info:
            ts_code = code + '.' + market
            for term in terms:
                job = self._create_kline_job_for_stock_term(
                    code, market, ts_code, term, last_market_open_day, latest_data, default_start_date
                )
                if job:
                    jobs.append(job)
        
        # 按优先级排序：日线 > 周线 > 月线
        term_priority = {'daily': 1, 'weekly': 2, 'monthly': 3}
        jobs.sort(key=lambda x: (term_priority.get(x['term'], 4), x['code']))
        
        logger.info(f"生成了 {len(jobs)} 个K线更新任务")
        return jobs

    def _create_kline_job_for_stock_term(self, code: str, market: str, ts_code: str, term: str, 
                                       last_market_open_day: str, 
                                       latest_data: dict, default_start_date: str) -> dict:
        """
        为单个股票单个周期创建K线更新任务
        """
        from datetime import datetime, timedelta
        
        # 获取该股票该周期的最新数据日期
        latest_date = latest_data.get(ts_code, {}).get(term)
        
        if not latest_date:
            # 没有数据，使用默认开始日期
            return {
                'code': code,
                'market': market,
                'ts_code': ts_code,
                'term': term,
                'start_date': default_start_date,
                'end_date': last_market_open_day,
                'reason': 'no_data'
            }
        
        latest_dt = datetime.strptime(latest_date, '%Y%m%d')
        last_market_dt = datetime.strptime(last_market_open_day, '%Y%m%d')
        
        # 根据不同的周期类型判断是否需要更新
        if term == 'daily':
            # 日线：直接比较日期
            if latest_dt < last_market_dt:
                start_date = (latest_dt + timedelta(days=1)).strftime('%Y%m%d')
                return {
                    'code': code,
                    'market': market,
                    'ts_code': ts_code,
                    'term': term,
                    'start_date': start_date,
                    'end_date': last_market_open_day,
                    'reason': 'daily_update'
                }
                
        elif term == 'weekly':
            # 周线：检查是否包含最新的完整周
            latest_week_start = latest_dt - timedelta(days=latest_dt.weekday())
            last_market_week_start = last_market_dt - timedelta(days=last_market_dt.weekday())
            
            if latest_week_start < last_market_week_start:
                # 需要更新：从最新周的下一个周开始
                next_week_start = latest_week_start + timedelta(days=7)
                start_date = next_week_start.strftime('%Y%m%d')
                return {
                    'code': code,
                    'market': market,
                    'ts_code': ts_code,
                    'term': term,
                    'start_date': start_date,
                    'end_date': last_market_open_day,
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
                    'code': code,
                    'market': market,
                    'ts_code': ts_code,
                    'term': term,
                    'start_date': start_date,
                    'end_date': last_market_open_day,
                    'reason': 'monthly_update'
                }
        
        # 不需要更新
        return None

    def execute_kline_jobs(self, jobs: list, batch_size: int = 10):
        """
        执行K线数据更新任务
        
        Args:
            jobs: 任务列表
            batch_size: 批处理大小
        """
        if not jobs:
            logger.info("没有需要更新的K线数据任务")
            return
        
        total_jobs = len(jobs)
        logger.info(f"开始执行 {total_jobs} 个K线数据更新任务")
        
        for i, job in enumerate(jobs):
            try:
                logger.info(f"执行任务 {i+1}/{total_jobs}: {job['code']} {job['term']} "
                          f"({job['start_date']} -> {job['end_date']})")
                
                # 这里调用具体的K线数据获取和保存逻辑
                self._fetch_and_save_kline_data(job)
                
                # 每处理一批任务后暂停一下，避免API限制
                if (i + 1) % batch_size == 0:
                    logger.info(f"已处理 {i+1}/{total_jobs} 个任务，暂停1秒...")
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"执行任务失败 {job['code']} {job['term']}: {e}")
                continue
        
        logger.info(f"K线数据更新任务执行完成，共处理 {total_jobs} 个任务")

    def _fetch_and_save_kline_data(self, job: dict):
        """
        获取并保存K线数据（具体实现）
        """
        # TODO: 实现具体的K线数据获取和保存逻辑
        # 这里需要调用Tushare API获取数据，然后保存到数据库
        logger.info(f"获取K线数据: {job['code']} {job['term']} "
                   f"({job['start_date']} -> {job['end_date']})")

    def renew_stock_kline_batch(self):
        """
        批量更新股票K线数据
        """
        # 获取所有股票代码和市场信息
        stock_index_data = self.storage.get_stock_index()
        stock_info = [(stock['code'], stock['market']) for stock in stock_index_data]
        
        # 定义周期和参数
        terms = ['daily', 'weekly', 'monthly']
        default_start_date = '20080101'
        
        # 生成更新任务
        jobs = self.generate_kline_update_jobs(
            stock_info, terms, self.last_market_open_day, default_start_date
        )
        
        # 执行任务
        self.execute_kline_jobs(jobs)

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












    # stock kline related
    def renew_stock_kline(self):
        """旧的单股票K线更新方法（保留兼容性）"""
        stock_index = self.storage.get_stock_index()

        for idx in stock_index:
            if self.storage.should_renew_stock_kline(idx['code'], 'daily', self.last_market_open_day):
                self.renew_stock_kline_by_code(idx['code'], 'daily')
            else:
                print(f"stock kline for {idx['code']} is up to date")

    def renew_stock_kline_by_code(self, code: str, term: str):
        """根据股票代码和周期更新K线数据"""
        # TODO: 实现具体的K线数据获取和保存逻辑
        logger.info(f"更新K线数据: {code} {term}")

    # 其他注释掉的代码保持不变...