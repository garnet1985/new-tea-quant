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
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class AKShare:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.storage = AKShareStorage(connected_db)
        self.service = AKShareService(is_verbose)
        self.is_verbose = is_verbose
        self.tu = None
        # 直接使用akshare的stock_zh_a_hist函数，避免递归调用
        self.api = stock_zh_a_hist
        
        # 配置重试和错误处理
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit_delay = 0.5  # 降低基础延迟到0.5秒
        
        # Tushare adj_factor API频率限制
        self.tushare_adj_factor_count = 0
        self.tushare_adj_factor_last_time = 0
        self.tushare_adj_factor_max_per_minute = 1000
        self.tushare_adj_factor_delay = 60 / self.tushare_adj_factor_max_per_minute  # 60秒 / 1000次 = 0.06秒每次
        
        # 添加线程锁，确保多线程环境下的限流安全
        import threading
        self.tushare_adj_factor_lock = threading.Lock()

    def inject_dependency(self, tu: Tushare):
        self.tu = tu
        return self
    
    def _tushare_adj_factor_rate_limit(self):
        """Tushare adj_factor API频率限制（线程安全）"""
        with self.tushare_adj_factor_lock:
            current_time = time.time()
            time_since_last = current_time - self.tushare_adj_factor_last_time
            
            # 如果距离上次请求时间太短，则等待
            if time_since_last < self.tushare_adj_factor_delay:
                sleep_time = self.tushare_adj_factor_delay - time_since_last
                time.sleep(sleep_time)
            
            self.tushare_adj_factor_last_time = time.time()
            self.tushare_adj_factor_count += 1
            
            # 每分钟重置计数器
            if self.tushare_adj_factor_count >= self.tushare_adj_factor_max_per_minute:
                if self.is_verbose:
                    logger.info(f"Tushare adj_factor API: 已调用 {self.tushare_adj_factor_count} 次，等待下一分钟...")
                time.sleep(60)  # 等待一分钟
                self.tushare_adj_factor_count = 0
                # 重置最后请求时间，确保等待后能继续处理
                self.tushare_adj_factor_last_time = time.time()

    def renew_stock_K_line_factors(self, latest_market_open_day: str, stock_index: list = None):
        if self.is_verbose:
            logger.info(f"Starting stock K-line factors renewal for {len(stock_index) if stock_index else 'all'} stocks")

        should_update, info = self.storage.should_update_adj_factors()
        
        if not should_update:   
            permission = input(info)
            if permission.lower() != 'y':
                return
        else:
            logger.info(info)
        
        return self.update_adj_factors_by_batch(stock_index, latest_market_open_day)

    def update_adj_factors_by_batch(self, stock_index: list, latest_market_open_day: str) -> None:
        jobs = self.build_jobs(stock_index, latest_market_open_day)
        self.execute_jobs(jobs)
        self.storage.update_last_update_time()

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
        # 增加并发数，但保持适度以避免API限制
        worker = FuturesWorker(max_workers=5, is_verbose=self.is_verbose)
        worker.set_job_executor(self.renew_adj_factors_for_single_stock)
        return worker.run_jobs(jobs)

    def renew_adj_factors_for_single_stock(self, job_data: Dict) -> None:
        latest_market_open_day = job_data['latest_market_open_day']

        latest_factor_in_db = self.storage.get_latest_factor(job_data['ts_code'])

        if latest_factor_in_db is None:
            db_latest_factor_change_date = data_default_start_date
        else:
            db_latest_factor_change_date = latest_factor_in_db['date']



        # 应用Tushare adj_factor API频率限制（在调用API之前）
        # self._tushare_adj_factor_rate_limit()
        
        # 获取Tushare的因子变化事件
        factors_events = self.tu.api.adj_factor(ts_code=job_data['ts_code'], start_date=db_latest_factor_change_date, end_date=latest_market_open_day)
        factor_changing_dates = self.service.get_factor_changing_dates(factors_events)
        
        if len(factor_changing_dates) == 0:
            if self.is_verbose:
                logger.info(f"✅ {job_data['ts_code']} 无新的复权因子变化，跳过更新")
            return
        
        # 使用robust的API调用方法
        qfq_k_lines = self._robust_stock_hist(
            symbol=job_data['code'], 
            period="daily", 
            start_date=db_latest_factor_change_date, 
            end_date=latest_market_open_day, 
            adjust="qfq"
        )
        
        if qfq_k_lines is None:
            if self.is_verbose:
                logger.error(f"无法获取 {job_data['ts_code']} 的QFQ数据，跳过处理")
            return
        
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

    def _robust_stock_hist(self, symbol: str, period: str = "daily", 
                          start_date: str = None, end_date: str = None, 
                          adjust: str = "qfq") -> Optional[pd.DataFrame]:
        """
        带重试机制的股票历史数据获取
        """
        max_retries = 2  # 减少重试次数
        base_delay = 1.0  # 减少基础延迟
        
        for attempt in range(max_retries):
            try:
                # 频率限制
                # self._rate_limit()
                
                # 随机选择User-Agent
                user_agent = random.choice(self.user_agents)
                
                # 设置请求头
                headers = {
                    'User-Agent': user_agent,
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                # 调用AKShare API
                result = stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )
                
                # 如果成功，重置延迟
                if attempt > 0:
                    self.rate_limit_delay = max(1.0, self.rate_limit_delay - 0.2)
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # 检查是否是限制类错误
                if any(keyword in error_msg.lower() for keyword in ['connection', 'timeout', 'proxy', 'blocked', 'rate limit']):
                    if self.is_verbose:
                        logger.warning(f"AKShare API限制错误 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                    
                    # 增加延迟，但设置上限
                    self.rate_limit_delay = min(3.0, self.rate_limit_delay * 1.2)
                    
                    # 指数退避延迟
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    if self.is_verbose:
                        logger.info(f"等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                    
                    continue
                else:
                    # 其他错误，直接抛出
                    if self.is_verbose:
                        logger.error(f"AKShare API调用失败: {error_msg}")
                    raise e
        
        # 所有重试都失败了
        if self.is_verbose:
            logger.error(f"AKShare API调用失败，已重试 {max_retries} 次")
        return None

    def _rate_limit(self):
        """实现请求频率限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # 如果距离上次请求时间太短，则等待
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # 每50个请求增加延迟，并设置上限
        if self.request_count % 50 == 0:
            self.rate_limit_delay = min(2.0, self.rate_limit_delay + 0.2)
        
        # 每200个请求重置延迟，避免无限增长
        if self.request_count % 200 == 0:
            self.rate_limit_delay = 0.5
