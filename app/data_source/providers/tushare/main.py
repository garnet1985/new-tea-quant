import pprint
import tushare as ts
from loguru import logger
from app.conf.conf import stock_index_indicators
from utils.worker import FuturesWorker, ThreadExecutionMode
# auth_token_file 现在从 config 中获取
from app.data_source.providers.tushare.main_service import TushareService
from app.data_source.providers.tushare.main_storage import TushareStorage
from app.data_source.providers.conf.conf import data_default_start_date
import warnings
from datetime import datetime
import time

# 导入新的组件
from .config import TushareConfig
from .rate_limiter import RateLimiterManager
from utils.progress.progress_tracker import ProgressTrackerManager
from .renewers import (
    PriceIndexesRenewer,
    UniversalRenewerManager
)


# 抑制tushare库的FutureWarning
warnings.filterwarnings('ignore', category=FutureWarning, module='tushare')

class Tushare:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.db = connected_db
        self.storage = TushareStorage(connected_db)
        self.is_verbose = is_verbose

        # 初始化配置管理器
        self.config = TushareConfig()
        
        # 初始化API
        self.use_token()
        self.api = ts.pro_api()
        
        # 初始化限流器管理器
        self.rate_limiter_manager = RateLimiterManager()
        
        # 初始化进度跟踪器管理器
        self.progress_tracker_manager = ProgressTrackerManager()
        
        # 初始化数据更新器（保留未被通用更新器替代的）
        self.price_indexes_renewer = PriceIndexesRenewer(
            db=connected_db, api=self.api, storage=self.storage, is_verbose=is_verbose
        )
        
        # 初始化通用更新器管理器
        self.universal_renewer_manager = UniversalRenewerManager(
            db=connected_db, api=self.api, storage=self.storage, is_verbose=is_verbose
        )
        
        # 获取限流器实例
        self.kline_rate_limiter = self.rate_limiter_manager.get_limiter(
            'K线数据',
            self.config.kline_rate_limit.max_per_minute,
            self.config.kline_rate_limit.buffer
        )
        
        self.corp_finance_rate_limiter = self.rate_limiter_manager.get_limiter(
            '企业财务数据',
            self.config.corp_finance_rate_limit.max_per_minute,
            self.config.corp_finance_rate_limit.buffer
        )
        
        # 线程局部 DB（用于每个工作线程独立复用同一个 DatabaseManager 与 Storage）
        import threading
        self._thread_local = threading.local()
        self._thread_dbs = []
        self._thread_dbs_lock = threading.Lock()

    
    # ================================ auth related ================================
    def get_token(self):
        try:
            with open(self.config.auth_token_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Token file not found at: {self.config.auth_token_file}. Please create file with token string inside.")

    def use_token(self):
        ts.set_token(self.get_token())

    # ================================ k line api rate limit ================================
    def _k_line_api_rate_limit(self):
        """Tushare K线数据API频率限制（使用新的限流器）"""
        self.kline_rate_limiter.acquire()

    # ================================ get latest market open day ================================
    async def get_latest_market_open_day(self):
        return TushareService.get_latest_market_open_day(self.api)

    # ================================ stock kline ================================
    async def renew_stock_k_lines(self, latest_market_open_day: str = None, stock_index: list = None):
        await self.renew_stock_k_lines_by_batch(latest_market_open_day, stock_index)

    async def renew_stock_k_lines_by_batch(self, latest_market_open_day: str = None, stock_index: list = None):
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
        jobs = TushareService.generate_kline_renew_jobs(stock_list, latest_market_open_day, self.storage)
        # 统计各类型任务数量
        term_counts = {}
        total_jobs = 0

        # 取消交互式确认，由调用方通过 actions 决定是否执行
        
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
        
        # 初始化K线数据进度跟踪器
        self.kline_progress_tracker = self.progress_tracker_manager.create_tracker(
            'kline',
            total_stocks,
            'K线数据',
            self.config.progress_show_details,
            True,  # 启用进度条模式
            True   # 启用固定位置模式
        )
        
        # 创建并行执行器
        worker = FuturesWorker(
            max_workers=10,
            execution_mode=ThreadExecutionMode.PARALLEL,
            enable_monitoring=True,
            timeout=3600.0,  # 等待最长1小时，确保所有股票任务完成后再继续
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
        if stats.get('timed_out'):
            logger.error(f"📉 K线更新超时: 完成 {stats.get('completed_jobs', 0)}/{stats.get('total_jobs', 0)}, 未完成 {stats.get('not_done_count', 0)}, 失败 {stats.get('failed_jobs', 0)}, 取消 {stats.get('cancelled_jobs', 0)}")
        
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
        
        # 所有任务完成后，关闭各线程数据库，确保写入落盘
        self._close_thread_dbs()
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

        # 获取线程局部的数据库与存储实例（开启线程安全与连接池），并在整个线程生命周期内复用
        local_storage = self._get_thread_storage()

        try:
            # 收集该股票的所有数据
            all_stock_data = []
            
            for job in stock_jobs:
                try:
                    # 获取K线数据
                    data = self.fetch_kline_data(job)
                    
                    if data is not None and not data.empty:
                        # 转换数据格式并添加到批量数据中
                        converted_data = local_storage.convert_kline_data_for_storage(data, job)
                        all_stock_data.extend(converted_data)

                except Exception as e:
                    logger.error(f"获取股票 {stock_key} {job['term']} 数据失败: {e}")
                    # 继续处理其他周期，不中断整个股票的处理
            
            # 当单只股票全部数据请求完成，存储一次
            if all_stock_data:
                local_storage.batch_save_stock_kline(all_stock_data)
                
                result = {
                    'stock_key': stock_key,
                    'status': 'success',
                    'records_count': len(all_stock_data),
                    'terms_processed': len(stock_jobs)
                }
            else:
                result = {
                    'stock_key': stock_key,
                    'status': 'no_data',
                    'records_count': 0,
                    'terms_processed': len(stock_jobs)
                }
            # 更新并打印进度
            self.kline_progress_tracker.update(
                stock_key,
                result['status'],
                f"状态: {result['status']}"
            )
            return result
                
        except Exception as e:
            logger.error(f"❌ 处理股票 {stock_key} 失败: {e}")
            # 失败也计入进度
            self.kline_progress_tracker.update(
                stock_key,
                'failed',
                f"失败: {e}"
            )
            raise  # 重新抛出异常，让JobWorker捕获并记录
        finally:
            # 不在每只股票结束时关闭，保持异步写入；统一在批次结束后关闭
            pass

    def _get_thread_storage(self) -> TushareStorage:
        if getattr(self._thread_local, 'storage', None) is not None:
            return self._thread_local.storage
        from utils.db.db_manager import DatabaseManager
        local_db = DatabaseManager(is_verbose=False, enable_thread_safety=True, use_connection_pool=True)
        local_storage = TushareStorage(local_db)
        self._thread_local.db = local_db
        self._thread_local.storage = local_storage
        with self._thread_dbs_lock:
            self._thread_dbs.append(local_db)
        return local_storage

    def _close_thread_dbs(self):
        with self._thread_dbs_lock:
            dbs = list(self._thread_dbs)
            self._thread_dbs.clear()
        for db in dbs:
            try:
                db.close()
            except Exception:
                pass

    def fetch_kline_data(self, job: dict):
        # 应用K线数据API频率限制
        self._k_line_api_rate_limit()
        
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

    # ================================ stock index ================================
    def renew_stock_index(self, latest_market_open_day: str = None):
        """
        更新股票指数数据
        """
        return self.universal_renewer_manager.renew('stock_index', latest_market_open_day)



    # ================================ price indexes ================================
    def renew_price_indexes(self, latest_market_open_day: str = None):
        """
        刷新宏观价格/景气度指标（CPI/PPI/PMI/货币供应量M0/M1/M2）到 `price_indexes` 基础表。
        - 主键: ['id', 'date']，此处 id 固定为 'CN'
        - date 取每月第一天，格式 YYYY-MM-01
        数据来源：
        - 货币供应量: cn_m（money supply） [tushare: doc_id=242]
        - CPI: cpi [tushare: doc_id=228]
        - PPI: ppi [tushare: doc_id=245]
        - PMI: pmi [tushare: doc_id=325]
        """
        return self.price_indexes_renewer.renew(latest_market_open_day)

    # ================================ LPR ================================
    def renew_LPR(self, latest_market_open_day: str = None):
        """
        刷新利率指标（LPR）到 `interest_rates` 基础表。
        """
        return self.universal_renewer_manager.renew('lpr', latest_market_open_day)



    # ================================ Shibor ================================
    def renew_Shibor(self, latest_market_open_day: str = None):
        """
        刷新利率指标（Shibor）到 `interest_rates` 基础表。
        """
        return self.universal_renewer_manager.renew('shibor', latest_market_open_day)


    # ================================ GDP ================================
    def renew_GDP(self, latest_market_open_day: str = None):
        """
        刷新GDP数据
        """
        return self.universal_renewer_manager.renew('gdp', latest_market_open_day)


    # ================================ corporate financial data ================================
    def renew_corporate_finance(self, latest_market_open_day: str = None):
        """
        更新企业财务数据
        
        Args:
            latest_market_open_day: 最新交易日，格式 YYYYMMDD
        """
        if not latest_market_open_day:
            latest_market_open_day = self.get_latest_market_open_day()
        
        # 获取数据更新范围：从默认开始日期到最近一个季度
        current_quarter = TushareService.to_quarter(latest_market_open_day)
        if not current_quarter:
            logger.warning(f"❌ 无法解析当前季度: {latest_market_open_day}")
            return
        
        # 计算上一个季度（因为当前季度的数据要等季度结束后才有）
        latest_quarter = TushareService.get_previous_quarter(current_quarter)
        if not latest_quarter:
            logger.warning(f"❌ 无法计算上一个季度: {current_quarter}")
            return
        
        # 获取默认开始日期的季度
        from app.data_source.providers.conf.conf import data_default_start_date
        start_quarter = TushareService.to_quarter(data_default_start_date)
        if not start_quarter:
            logger.warning(f"❌ 无法解析默认开始季度: {data_default_start_date}")
            return
        
        # 获取股票列表
        stock_index = self.storage.load_stock_index()
        if not stock_index:
            logger.warning("❌ 没有股票数据，跳过企业财务更新")
            return
        
        # 构建更新任务
        jobs = self._build_corporate_finance_jobs(stock_index, start_quarter, latest_quarter)
        
        if not jobs:
            logger.info("✅ 所有股票的企业财务数据都是最新的")
            return
        
        logger.info(f"📊 企业财务数据更新任务: {len(jobs)} 个任务需要执行")
        
        # 初始化进度跟踪器
        self.corp_finance_progress_tracker = self.progress_tracker_manager.create_tracker(
            'corp_finance',
            len(jobs),
            '企业财务数据',
            self.config.progress_show_details,
            True,  # 启用进度条模式
            True   # 启用固定位置模式
        )
        
        # 执行多线程更新
        self._execute_corporate_finance_jobs(jobs)
        
        logger.info("✅ 企业财务数据更新完成")

    def _build_corporate_finance_jobs(self, stock_index: list, start_quarter: str, end_quarter: str) -> list:
        """
        构建企业财务数据更新任务
        
        Args:
            stock_index: 股票列表
            start_quarter: 开始季度，格式 YYYYQ{N}
            end_quarter: 结束季度，格式 YYYYQ{N}
            
        Returns:
            list: 需要更新的股票任务列表
        """
        jobs = []
        
        # 获取数据库中每只股票的最新财务数据季度
        latest_quarters = self._get_latest_corporate_finance_quarters()
        
        # 将季度转换为日期范围
        start_date, _ = TushareService.quarter_to_date_range(start_quarter)
        _, end_date = TushareService.quarter_to_date_range(end_quarter)
        
        for stock in stock_index:
            stock_id = stock['id']
            latest_quarter = latest_quarters.get(stock_id)
            
            # 如果股票没有数据或数据落后，则需要更新
            if not latest_quarter or latest_quarter < end_quarter:
                jobs.append({
                    'stock_id': stock_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'start_quarter': start_quarter,
                    'end_quarter': end_quarter,
                    'latest_quarter': latest_quarter
                })
        
        return jobs

    def _get_latest_corporate_finance_quarters(self) -> dict:
        """
        获取每只股票的最新财务数据季度
        
        Returns:
            dict: {stock_id: latest_quarter}
        """
        try:
            table = self.db.get_table_instance('corporate_finance')
            query = """
                SELECT id, MAX(quarter) as latest_quarter 
                FROM corporate_finance 
                GROUP BY id
            """
            
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                
            return {row['id']: row['latest_quarter'] for row in results}
            
        except Exception as e:
            logger.error(f"❌ 获取最新财务数据季度失败: {e}")
            return {}

    def _execute_corporate_finance_jobs(self, jobs: list):
        """
        使用多线程执行企业财务数据更新任务
        
        Args:
            jobs: 更新任务列表
        """
        if not jobs:
            return
        
        # 创建并行执行器
        corp_finance_config = self.config.get_corp_finance_config()
        worker = FuturesWorker(
            max_workers=corp_finance_config['worker'].max_workers,
            execution_mode=ThreadExecutionMode.PARALLEL,
            enable_monitoring=True,
            timeout=corp_finance_config['worker'].timeout,
            is_verbose=self.is_verbose,
            debug=False
        )
        
        # 设置任务执行函数
        worker.set_job_executor(self._process_single_corporate_finance_job)
        
        # 准备任务数据
        worker_jobs = []
        for i, job in enumerate(jobs):
            worker_jobs.append({
                'id': f"corp_fin_{i}",
                'data': job
            })
        
        # 执行任务
        logger.info(f"📊 开始公司财务数据更新 配置: {worker.max_workers}个线程并行，限流每分钟请求{corp_finance_config['rate_limit'].actual_limit}次.")
        stats = worker.run_jobs(worker_jobs)
        
        # 打印执行统计
        worker.print_stats()
        if stats.get('timed_out'):
            logger.error(f"📉 企业财务数据更新超时: 完成 {stats.get('completed_jobs', 0)}/{stats.get('total_jobs', 0)}")
        
        # 关闭线程局部数据库
        self._close_thread_dbs()

    def _process_single_corporate_finance_job(self, job_data: dict):
        """
        处理单个股票的企业财务数据更新任务
        
        Args:
            job_data: 任务数据
            
        Returns:
            dict: 处理结果
        """
        stock_id = job_data['stock_id']
        start_date = job_data['start_date']
        end_date = job_data['end_date']
        start_quarter = job_data['start_quarter']
        end_quarter = job_data['end_quarter']
        latest_quarter = job_data.get('latest_quarter')
        
        # 获取线程局部的数据库与存储实例
        local_storage = self._get_thread_storage()
        
        try:
            # 获取企业财务数据
            data = self._fetch_corporate_finance_data(stock_id, start_date, end_date)
            
            if data is not None and not data.empty:
                # 转换并保存数据
                converted_data = local_storage.convert_corporate_finance_data_for_storage(data)
                local_storage.batch_save_corporate_finance(converted_data)
                
                result = {
                    'stock_id': stock_id,
                    'status': 'success',
                    'records_count': len(converted_data),
                    'quarter_range': f"{start_quarter}~{end_quarter}"
                }
                
                # 更新进度
                self.corp_finance_progress_tracker.update(
                    stock_id,
                    'success',
                    f"完成: {start_quarter}~{end_quarter} ({len(converted_data)}条记录)"
                )
            else:
                result = {
                    'stock_id': stock_id,
                    'status': 'no_data',
                    'records_count': 0,
                    'quarter_range': f"{start_quarter}~{end_quarter}"
                }
                logger.warning(f"⚠️ {stock_id} 企业财务数据为空: {start_quarter}~{end_quarter}")
                
                # 更新进度（即使没有数据也算完成）
                self.corp_finance_progress_tracker.update(
                    stock_id,
                    'no_data',
                    f"无数据: {start_quarter}~{end_quarter}"
                )
                
        except Exception as e:
            logger.error(f"❌ {stock_id} 企业财务数据更新失败: {e}")
            result = {
                'stock_id': stock_id,
                'status': 'error',
                'error': str(e),
                'quarter_range': f"{start_quarter}~{end_quarter}"
            }
            
            # 更新进度（即使出错也算完成）
            self.corp_finance_progress_tracker.update(
                stock_id,
                'error',
                f"失败: {e}"
            )
        
        return result

    def _fetch_corporate_finance_data(self, stock_id: str, start_date: str, end_date: str):
        """
        获取企业财务数据
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            
        Returns:
            DataFrame: 企业财务数据
        """
        # 应用API频率限制
        self.corp_finance_rate_limiter.acquire()
        
        try:
            # 调用Tushare企业财务数据API
            data = self.api.fina_indicator(
                ts_code=stock_id,
                start_date=start_date,
                end_date=end_date
            )
            
            return data
            
        except Exception as e:
            logger.error(f"❌ 获取 {stock_id} 企业财务数据失败: {e}")
            return None

    # ================================ stock index indicator ================================
    def renew_stock_index_indicator(self, latest_market_open_day: str = None):
        """
        刷新股票指数指标数据
        获取主要股票指数的日K线数据（上证指数、深证成指、沪深300、创业板指、科创50）
        """
        return self.universal_renewer_manager.renew('stock_index_indicator', latest_market_open_day)

    # ================================ stock index indicator weight ================================
    def renew_stock_index_indicator_weight(self, latest_market_open_day: str = None):
        """
        刷新股票指数指标权重数据
        获取主要股票指数的成分股权重数据
        """
        return self.universal_renewer_manager.renew('stock_index_indicator_weight', latest_market_open_day)

    # ================================ industry capital flow ================================
    def renew_industry_capital_flow(self, latest_market_open_day: str = None):
        """
        刷新行业资金流向数据
        获取同花顺行业资金流向数据
        """
        return self.universal_renewer_manager.renew('industry_capital_flow', latest_market_open_day)

