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
        
        # Tushare adj_factor API频率限制
        self.tushare_adj_factor_count = 0
        self.tushare_adj_factor_last_time = 0
        self.tushare_adj_factor_max_per_minute = 800  # Tushare限制：每分钟最多800次请求
        self.tushare_adj_factor_safe_limit = 750      # 安全起见，每批处理750次
        
        # 添加线程锁，确保多线程环境下的限流安全
        import threading
        self.tushare_adj_factor_lock = threading.Lock()

    def inject_dependency(self, tu: Tushare):
        self.tu = tu
        return self
    
    def _tushare_adj_factor_rate_limit(self):
        """
        Tushare adj_factor API频率限制（线程安全）
        优化版本：支持批量处理，快速达到限制后等待
        """
        with self.tushare_adj_factor_lock:
            current_time = time.time()
            
            # 如果是第一次调用，初始化时间
            if self.tushare_adj_factor_last_time == 0:
                self.tushare_adj_factor_last_time = current_time
            
            # 检查是否到了新的一分钟
            time_since_start = current_time - self.tushare_adj_factor_last_time
            
            if time_since_start >= 60:
                # 新的一分钟，重置计数器
                self.tushare_adj_factor_count = 0
                self.tushare_adj_factor_last_time = current_time
                logger.debug(f"🔄 New minute window started for Tushare API")
            
            # 检查是否达到限制
            if self.tushare_adj_factor_count >= self.tushare_adj_factor_safe_limit:
                # 达到安全限制，等待到下一分钟
                remaining_time = 60 - time_since_start
                if remaining_time > 0:
                    logger.info(f"⏳ Tushare API limit reached ({self.tushare_adj_factor_count}/{self.tushare_adj_factor_safe_limit}). Waiting {remaining_time:.1f}s for next minute...")
                    time.sleep(remaining_time)
                    # 重置计数器
                    self.tushare_adj_factor_count = 0
                    self.tushare_adj_factor_last_time = time.time()
            
            # 增加计数器
            self.tushare_adj_factor_count += 1

    def renew_stock_K_line_factors(self, latest_market_open_day: str, stock_index: list = None):
        should_update, info = self.storage.should_update_adj_factors()
        
        if not should_update:   
            permission = input(info)
            if permission.lower() != 'y':
                logger.info("❌ User chose not to update adj factors")
                return
        else:
            logger.info(info)
        
        return self.update_adj_factors_by_batch(stock_index, latest_market_open_day)

    def update_adj_factors_by_batch(self, stock_index: list, latest_market_open_day: str) -> None:
        jobs = self.build_jobs(stock_index, latest_market_open_day)
        
        result = self.execute_jobs(jobs)
        
        self.storage.update_last_update_time()

    def build_jobs(self, stock_index: list, latest_market_open_day: str) -> List[Dict]:
        jobs = []
        for stock_info in stock_index:
            # 使用 ts_code 作为 id
            ts_code = stock_info['id']
            jobs.append({
                'id': f'fetch_{ts_code}_adjust_factors',
                'data': {
                    'ts_code': ts_code,
                    'name': stock_info['name'],
                    'latest_market_open_day': latest_market_open_day
                }
            })
        return jobs

    def execute_jobs(self, jobs: List[Dict]) -> bool:
        """
        智能分批执行任务，优化Tushare API限流
        策略：快速并行处理750个请求，然后等待下一分钟
        """
        if not jobs:
            logger.info("No jobs to execute")
            return True
        
        total_jobs = len(jobs)
        logger.info(f"🚀 Starting execution of {total_jobs} jobs with smart rate limiting...")
        
        # 分批处理，每批750个（安全限制）
        batch_size = self.tushare_adj_factor_safe_limit
        total_batches = (total_jobs + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_jobs)
            batch_jobs = jobs[start_idx:end_idx]
            
            logger.info(f"🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_jobs)} jobs)")
            
            # 使用高并发快速处理当前批次
            worker = FuturesWorker(max_workers=20, is_verbose=False)
            worker.set_job_executor(self.renew_adj_factors_for_single_stock)
            
            # 执行当前批次
            result = worker.run_jobs(batch_jobs)
            
            # 如果不是最后一批，需要等待下一分钟
            if batch_num < total_batches - 1:
                logger.info(f"⏳ Batch {batch_num + 1} completed. Waiting for next minute window...")
                time.sleep(60)  # 等待下一分钟
                logger.info(f"✅ Next minute window started. Continuing with batch {batch_num + 2}...")
        
        logger.info(f"🎉 All {total_jobs} jobs completed successfully!")
        return True

    def renew_adj_factors_for_single_stock(self, job_data: Dict) -> None:
        ts_code = job_data['ts_code']
        latest_market_open_day = job_data['latest_market_open_day']

        latest_factor_in_db = self.storage.get_latest_factor(ts_code)

        if latest_factor_in_db is None:
            db_latest_factor_change_date = data_default_start_date
        else:
            db_latest_factor_change_date = latest_factor_in_db['date']



        # 应用Tushare adj_factor API频率限制（在调用API之前）
        self._tushare_adj_factor_rate_limit()
        
        # 获取Tushare的因子变化事件
        factors_events = self.tu.api.adj_factor(ts_code=ts_code, start_date=db_latest_factor_change_date, end_date=latest_market_open_day)
        
        factor_changing_dates = self.service.get_factor_changing_dates(factors_events)
        
        # 检查是否有新的因子变化需要处理
        if len(factor_changing_dates) == 0:
            logger.info(f"✅ {ts_code}({job_data['name']}) 无新的复权因子变化，跳过更新")
            return
        
        # 获取所有需要重新计算的日期（按时间顺序排序）
        all_changing_dates = sorted(factor_changing_dates)
        earliest_date = all_changing_dates[0]

        # 删除从最早变化日期开始的所有因子
        self.storage.clear_adj_factors_from_date(ts_code, earliest_date)

        logger.info(f"🌐  Fetching QFQ data for {ts_code} from {earliest_date} to {latest_market_open_day}...")
        
        # 调用一次AKShare API获取从最早变化日期到最新的所有数据
        # 这样可以避免多次API调用，减少被block的风险
        qfq_k_lines = self._robust_stock_hist(
            symbol=ts_code, 
            period="daily", 
            start_date=earliest_date, 
            end_date=latest_market_open_day, 
            adjust="qfq"
        )
        
        if qfq_k_lines is None:
            logger.error(f"❌ 无法获取 {ts_code} 的QFQ数据，跳过处理")
            return
        
        # 基于获取的数据计算所有需要的复权因子
        self.renew_factors(all_changing_dates, qfq_k_lines, job_data)


    def renew_factors(self, dates: List[str], qfq_k_lines: pd.DataFrame, job_data: Dict):
        ts_code = job_data['ts_code']
        
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
                    ts_code,              # ts_code
                    factor['date'],       # date
                    factor['qfq_factor'], # qfq_factor
                    factor['hfq_factor']  # hfq_factor
                ))
            
            logger.info(f"💾 Storing {len(factors_data)} factors to database...")
            result = self.storage.batch_upsert_adj_factors(factors_data)
            
            # 更新最后更新时间
            if result:
                self.storage.update_last_update_time()
        else:
            logger.warning(f"⚠️  No factors to store for {ts_code}")
        
        return factors
    
    def calc_factors(self, date: str, job_data: Dict, qfq_data: pd.DataFrame) -> Optional[Dict]:
        ts_code = job_data['ts_code']
        
        # 从数据库获取不复权收盘价
        raw_close = self.storage.get_close_price(ts_code, date)

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
        result = {
            'date': date,
            'qfq_factor': qfq_factor,
            'hfq_factor': 0  # 后复权因子设为0，因为我们不计算它
        }
        
        return result

    def _robust_stock_hist(self, symbol: str, period: str = "daily", 
                          start_date: str = None, end_date: str = None, 
                          adjust: str = "qfq") -> Optional[pd.DataFrame]:
        """
        带重试机制的股票历史数据获取
        """
        # 解析股票代码，去掉市场后缀
        pure_symbol = DataSourceService.parse_ts_code(symbol)[0]
        
        max_retries = 2  # 减少重试次数
        base_delay = 1.0  # 减少基础延迟
        
        for attempt in range(max_retries):
            try:
                
                
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
                
                # 调用AKShare API，使用解析后的纯数字代码
                result = stock_zh_a_hist(
                    symbol=pure_symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )
                

                
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # 检查是否是限制类错误
                if any(keyword in error_msg.lower() for keyword in ['connection', 'timeout', 'proxy', 'blocked', 'rate limit']):
                    if self.is_verbose:
                        logger.warning(f"AKShare API限制错误 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                    

                    
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


