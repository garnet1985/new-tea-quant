import pprint
import tushare as ts
from loguru import logger
from utils.worker.futures_worker import FuturesWorker, ExecutionMode
from app.data_source.providers.tushare.main_settings import auth_token_file
from app.data_source.providers.tushare.main_service import TushareService
from app.data_source.providers.tushare.main_storage import TushareStorage
import warnings
import time


# 抑制tushare库的FutureWarning
warnings.filterwarnings('ignore', category=FutureWarning, module='tushare')

class Tushare:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.db = connected_db
        self.storage = TushareStorage(connected_db)
        self.service = TushareService()

        self.is_verbose = is_verbose

        self.use_token();
        self.api = ts.pro_api()
        
        # 添加Tushare K线数据API频率限制
        self.kline_api_count = 0
        self.kline_api_last_time = 0
        self.kline_api_max_per_minute = 750  # 降低到750，为多线程并发留出缓冲
        
        # 添加线程锁，确保多线程环境下的限流安全
        import threading
        self.kline_api_lock = threading.Lock()

    def _kline_api_rate_limit(self):
        """Tushare K线数据API频率限制（线程安全）"""
        with self.kline_api_lock:
            current_time = time.time()
            
            # 检查是否需要重置计数器（每分钟重置一次）
            if current_time - self.kline_api_last_time >= 60:
                self.kline_api_count = 0
                self.kline_api_last_time = current_time
            
            # 如果当前分钟内的请求数已达到限制，则等待到下一分钟
            if self.kline_api_count >= self.kline_api_max_per_minute:
                wait_time = 60 - (current_time - self.kline_api_last_time)
                if wait_time > 0:
                    logger.info(f"Tushare K线API: 当前分钟已调用 {self.kline_api_count} 次，等待 {wait_time:.1f} 秒到下一分钟...")
                    time.sleep(wait_time)
                    self.kline_api_count = 0
                    self.kline_api_last_time = time.time()
            
            # 增加请求计数
            self.kline_api_count += 1

    async def get_latest_market_open_day(self):
        return self.service.get_latest_market_open_day(self.api)


    async def renew_stock_K_lines(self, latest_market_open_day: str = None, stock_index: list = None):
       await self.renew_stock_K_lines_by_batch(latest_market_open_day, stock_index)


    async def renew_global_economic_data(self):
        # TODO: implement when necessary
        pass

    async def renew_corporate_finance_data(self):
        # TODO: implement when necessary
        pass
    

    async def renew_stock_K_lines_by_batch(self, latest_market_open_day: str = None, stock_index: list = None):
        """
        批量更新股票K线数据
        """
        
        # 获取所有股票代码和市场信息
        stock_list = []
        
        # 处理统一格式的股票指数数据
        for row in stock_index:
            stock_id = row['id']
            stock_list.append(stock_id)
        
        # 生成按股票分组的更新任务
        jobs = self.service.generate_kline_renew_jobs(stock_list, latest_market_open_day, self.storage)
        # 统计各类型任务数量
        term_counts = {}
        total_jobs = 0

        permission = input(f"共有 {len(jobs)} 个股票K线需要更新，是否更新? y:更新 | 其他任意键:不更新")
        if permission.lower() != 'y':
            return
        
        for stock_key, stock_jobs in jobs.items():
            for job in stock_jobs:
                term = job['term']
                term_counts[term] = term_counts.get(term, 0) + 1
                total_jobs += 1
        
        logger.info(f"📊 data renew jobs:")
        logger.info(f"  total: {total_jobs}")
        for term, count in term_counts.items():
            logger.info(f"  - {term} k-line fetch jobs: {count}")

        if len(jobs) > 0:
            self.execute_stock_kline_renew_jobs(jobs)
            
            # 等待异步写入完成
            await self.db.wait_for_writes(timeout=60)
        else:
            logger.info("All K-lines are up to date")

        logger.info(f"✅ Renew stock kline jobs complete. total jobs: {len(jobs)}")        


    def execute_stock_kline_renew_jobs(self, jobs: dict):
        """
        使用FuturesWorker并行执行K线数据获取任务
        
        Args:
            jobs: 按股票分组的任务字典 {stock_key: [job_info1, job_info2, ...]}
        """
        if not jobs:
            logger.info("No kline renew jobs")
            return
        
        total_stocks = len(jobs)
        logger.info(f"Start to execute {total_stocks} stocks with FuturesWorker")
        
        # 创建并行执行器
        worker = FuturesWorker(
            max_workers=10,
            execution_mode=ExecutionMode.PARALLEL,
            enable_monitoring=True,
            timeout=60.0,  # 增加超时时间，因为数据获取可能需要更长时间
            is_verbose=self.is_verbose,  # 关闭详细日志，只保留进度信息
            debug=False    # 关闭调试日志
        )
        
        # 设置任务执行函数
        worker.set_job_executor(self.process_single_stock_jobs)
        
        # 准备任务数据
        worker_jobs = []
        for stock_key, stock_jobs in jobs.items():
            worker_jobs.append({
                'id': stock_key,
                'data': {
                    'stock_key': stock_key,
                    'stock_jobs': stock_jobs
                }
            })
        
        # 执行任务
        stats = worker.run_jobs(worker_jobs)
        
        # 打印执行统计
        worker.print_stats()
        
        # 获取结果并分析
        results = worker.get_results()
        success_count = sum(1 for r in results if r.status.value == 'completed')
        failed_count = sum(1 for r in results if r.status.value == 'failed')
        
        logger.info(f"✅ 任务执行完成: 成功 {success_count}/{total_stocks}, 失败 {failed_count}")
        
        # 处理失败的任务
        if failed_count > 0:
            failed_jobs = [r for r in results if r.status.value == 'failed']
            for failed in failed_jobs:
                logger.error(f"❌ 股票 {failed.job_id} 处理失败: {failed.error}")
        
        return stats

    def process_single_stock_jobs(self, job_data: dict):
        """
        处理单个股票的所有K线数据获取任务
        
        Args:
            job_data: 任务数据，包含 stock_key 和 stock_jobs
            
        Returns:
            dict: 处理结果
        """
        stock_key = job_data['stock_key']
        stock_jobs = job_data['stock_jobs']

        try:
            # 收集该股票的所有数据
            all_stock_data = []
            
            for job in stock_jobs:
                try:
                    # 获取K线数据
                    data = self.fetch_kline_data(job)
                    
                    if data is not None and not data.empty:
                        # 转换数据格式并添加到批量数据中
                        converted_data = self.storage.convert_kline_data_for_storage(data, job)
                        all_stock_data.extend(converted_data)

                except Exception as e:
                    logger.error(f"获取股票 {stock_key} {job['term']} 数据失败: {e}")
                    # 继续处理其他周期，不中断整个股票的处理
            
            # 当单只股票全部数据请求完成，存储一次
            if all_stock_data:
                self.storage.batch_save_stock_kline(all_stock_data)
                
                return {
                    'stock_key': stock_key,
                    'status': 'success',
                    'records_count': len(all_stock_data),
                    'terms_processed': len(stock_jobs)
                }
            else:
                return {
                    'stock_key': stock_key,
                    'status': 'no_data',
                    'records_count': 0,
                    'terms_processed': len(stock_jobs)
                }
                
        except Exception as e:
            logger.error(f"❌ 处理股票 {stock_key} 失败: {e}")
            raise  # 重新抛出异常，让JobWorker捕获并记录

    def fetch_kline_data(self, job: dict):
        # 应用K线数据API频率限制
        self._kline_api_rate_limit()
        
        try:
            if job['term'] == 'daily':
                return self.api.daily(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
            elif job['term'] == 'weekly':
                return self.api.weekly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
            elif job['term'] == 'monthly':
                return self.api.monthly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
        except Exception as e:
            if self.is_verbose:
                logger.error(f"Tushare K线API调用失败: {e}")
            raise e


    def renew_stock_index(self, latest_market_open_day: str = None, is_force=False):
        meta_info_key = 'stock_index_last_update'

        if is_force:
            idx_data = self.request_stock_index()
            self.storage.save_stock_index(idx_data)
            self.storage.save_meta_info(meta_info_key, latest_market_open_day)
            return self.service.to_unified_stock_index_format(idx_data)

        last_update = self.storage.get_meta_info_by_key(meta_info_key)

        if last_update is None:
            idx_data = self.request_stock_index()
            self.storage.save_stock_index(idx_data)
            self.storage.set_meta_info_by_key(meta_info_key, latest_market_open_day)
            return self.service.to_unified_stock_index_format(idx_data)
        else:
            if last_update < latest_market_open_day:
                idx_data = self.request_stock_index()
                self.storage.save_stock_index(idx_data)
                self.storage.set_meta_info_by_key(meta_info_key, latest_market_open_day)
                return self.service.to_unified_stock_index_format(idx_data)
            else:
                logger.info('stock index is up to date, no need to renew')
                idx_data = self.storage.load_stock_index()  
                return self.service.to_unified_stock_index_format(idx_data)

    def request_stock_index(self):
        fields = 'ts_code,name,area,industry,market,exchange,list_date'
        stock_status = 'L'
        data = self.api.stock_basic(exchange='', list_status=stock_status, fields=fields)
        
        # 统一转换为列表格式，保持数据格式一致
        if hasattr(data, 'to_dict'):
            return data.to_dict('records')
        elif isinstance(data, list):
            return data
        else:
            return [data]

    
    # auth related
    def get_token(self):
        try:
            with open(auth_token_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Token file not found at: {auth_token_file}. Please create file with token string inside.")

    def use_token(self):
        ts.set_token(self.get_token())