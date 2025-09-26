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
    def renew_stock_index(self, latest_market_open_day: str = None, is_force=False):

        should_renew = False

        is_index_empty = self.storage.is_index_empty()

        if is_index_empty:
            is_force = True

        # 直接从stock_index表获取最新的lastUpdate
        last_renew_time = self.storage.stock_index_table.load_latest_last_update()

        last_dt = TushareService.to_date(last_renew_time)
        latest_dt = TushareService.to_date(latest_market_open_day)

        should_renew = is_force or last_dt is None or (latest_dt is not None and last_dt < latest_dt)

        if should_renew:
            new_idx_data = self.request_stock_index()
            if new_idx_data is not None and len(new_idx_data) > 0:
                # 保存成功后直接返回数据，不需要更新meta_info表
                save_success = self.storage.save_stock_index(new_idx_data)
                if save_success:
                    return TushareService.to_unified_stock_index_format(new_idx_data)
                else:
                    logger.error("❌ 股票指数数据保存失败，保持使用现有数据库数据")
                    return self.storage.load_stock_index()
            else:
                logger.error("❌ 股票列表返回结果为空, 检查tushare API是否正常，保持使用现有数据库数据")
                return self.storage.load_stock_index()
        else:
            logger.info(f"🔍 股票目录已经是最新，直接使用数据库数据:  {latest_market_open_day}")
            return self.storage.load_stock_index()


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
        参考: `https://tushare.pro/document/2?doc_id=242`, `https://tushare.pro/document/2?doc_id=228`, `https://tushare.pro/document/2?doc_id=245`, `https://tushare.pro/document/2?doc_id=325`
        """
        # 统一起止区间（与K线一致）：若未显式传入，则用配置默认起点 → 最新交易日
        start_m = TushareService.to_yyyymm(data_default_start_date)
        end_m = TushareService.to_yyyymm(latest_market_open_day) or datetime.now().strftime('%Y%m')

        by_month = {}

        # 小工具：调试打印
        def _log_df(name: str, df):
            if not self.is_verbose:
                return
            try:
                cols = list(df.columns) if df is not None else []
                logger.info(f"price_indexes | {name} cols: {cols}")
                if df is not None and not df.empty:
                    logger.info(f"price_indexes | {name} head: {df.head(3).to_dict('records')}")
            except Exception:
                pass

        # 1) Money Supply: cn_m
        try:
            df_m = self.api.cn_m(start_m=start_m, end_m=end_m)
            _log_df('cn_m', df_m)
            if df_m is not None and not df_m.empty:
                for _, r in df_m.iterrows():
                    m = str(r.get('month') or r.get('date') or '')
                    if not m:
                        continue
                    row = by_month.setdefault(m, {})
                    row['M0'] = TushareService.safe_to_float(r.get('m0'))
                    row['M0_yoy'] = TushareService.safe_to_float(r.get('m0_yoy'))
                    row['M0_mom'] = TushareService.safe_to_float(r.get('m0_mom'))
                    row['M1'] = TushareService.safe_to_float(r.get('m1'))
                    row['M1_yoy'] = TushareService.safe_to_float(r.get('m1_yoy'))
                    row['M1_mom'] = TushareService.safe_to_float(r.get('m1_mom'))
                    row['M2'] = TushareService.safe_to_float(r.get('m2'))
                    row['M2_yoy'] = TushareService.safe_to_float(r.get('m2_yoy'))
                    row['M2_mom'] = TushareService.safe_to_float(r.get('m2_mom'))
        except Exception as e:
            if self.is_verbose:
                logger.error(f"cn_m fetch failed: {e}")

        # 2) CPI
        try:
            df_cpi = self.api.cn_cpi(
                start_m=start_m,
                end_m=end_m,
                fields='month,nt_val,nt_yoy,nt_mom'
            )
            _log_df('cpi', df_cpi)

            if df_cpi is not None and not df_cpi.empty:
                for _, r in df_cpi.iterrows():
                    m = str(r.get('month') or r.get('date') or '')
                    if not m:
                        continue
                    row = by_month.setdefault(m, {})
                    # Fields per user: nt_val, nt_val_yoy, nt_val_mom
                    row['CPI'] = TushareService.safe_to_float(r.get('nt_val'))
                    row['CPI_yoy'] = TushareService.safe_to_float(r.get('nt_yoy'))
                    row['CPI_mom'] = TushareService.safe_to_float(r.get('nt_mom'))
        except Exception as e:
            logger.error(f"cpi fetch failed: {e}")

        # 3) PPI
        try:
            df_ppi = self.api.cn_ppi(
                start_m=start_m,
                end_m=end_m,
                fields='month,ppi_accu,ppi_yoy,ppi_mom'
            )
            _log_df('ppi', df_ppi)
            if df_ppi is not None and not df_ppi.empty:
                for _, r in df_ppi.iterrows():
                    m = str(r.get('month') or r.get('date') or '')
                    if not m:
                        continue
                    row = by_month.setdefault(m, {})
                    # Fields per user: ppi_accu, ppi_mom, ppi_yoy

                    row['PPI'] = TushareService.safe_to_float(r.get('ppi_accu'))
                    row['PPI_yoy'] = TushareService.safe_to_float(r.get('ppi_yoy'))
                    row['PPI_mom'] = TushareService.safe_to_float(r.get('ppi_mom'))
        except Exception as e:
            logger.error(f"ppi fetch failed: {e}")

        # 4) PMI
        try:
            # 限定返回字段，确保含 month 和四个指标
            df_pmi = self.api.cn_pmi(
                start_m=start_m,
                end_m=end_m,
                fields='month,pmi010000,pmi010100,pmi010200,pmi010300'
            )
            _log_df('pmi', df_pmi)

            if df_pmi is not None and not df_pmi.empty:
                for _, r in df_pmi.iterrows():
                    # month 可能为 'month' 或 'MONTH'
                    m = r.get('month') if 'month' in r else r.get('MONTH')
                    m = '' if m is None else str(m).strip()
                    if not m:
                        continue
                    row = by_month.setdefault(m, {})
                    row['PMI'] = TushareService.safe_to_float(r.get('pmi010000') or r.get('PMI010000'))
                    row['PMI_l_scale'] = TushareService.safe_to_float(r.get('pmi010100') or r.get('PMI010100'))
                    row['PMI_m_scale'] = TushareService.safe_to_float(r.get('pmi010200') or r.get('PMI010200'))
                    row['PMI_s_scale'] = TushareService.safe_to_float(r.get('pmi010300') or r.get('PMI010300'))
        except Exception as e:
            logger.error(f"pmi fetch failed: {e}")

        # Assemble rows
        records = []
        for m, vals in by_month.items():
            # 解析月份为 YYYY-MM-01
            dt = None
            for fmt in ('%Y%m', '%Y-%m', '%Y-%m-%d', '%Y/%m/%d'):
                try:
                    dt = datetime.strptime(m, fmt).strftime('%Y-%m-01')
                    break
                except ValueError:
                    continue
            if not dt:
                continue
            rec = {
                # per user: use YYYYMM string as id
                'id': m,
                'date': dt,
                'CPI': vals.get('CPI', 0.0),
                'CPI_yoy': vals.get('CPI_yoy', 0.0),
                'CPI_mom': vals.get('CPI_mom', 0.0),
                'PPI': vals.get('PPI', 0.0),
                'PPI_yoy': vals.get('PPI_yoy', 0.0),
                'PPI_mom': vals.get('PPI_mom', 0.0),
                'PMI': vals.get('PMI', 0.0),
                'PMI_l_scale': vals.get('PMI_l_scale', 0.0),
                'PMI_m_scale': vals.get('PMI_m_scale', 0.0),
                'PMI_s_scale': vals.get('PMI_s_scale', 0.0),
                'M0': vals.get('M0', 0.0),
                'M0_yoy': vals.get('M0_yoy', 0.0),
                'M0_mom': vals.get('M0_mom', 0.0),
                'M1': vals.get('M1', 0.0),
                'M1_yoy': vals.get('M1_yoy', 0.0),
                'M1_mom': vals.get('M1_mom', 0.0),
                'M2': vals.get('M2', 0.0),
                'M2_yoy': vals.get('M2_yoy', 0.0),
                'M2_mom': vals.get('M2_mom', 0.0)
            }
            records.append(rec)

        if not records:
            logger.info("价格指数: 没有数据需要更新")
            return

        try:
            table = self.db.get_table_instance('price_indexes')
            table.replace(records, ['id', 'date'])
            logger.info(f"✅ 价格指数 更新完成: {len(records)} 条")
        except Exception as e:
            logger.error(f"❌ 价格指数 更新失败: {e}")

    # ================================ LPR ================================
    def renew_LPR(self, latest_market_open_day: str = None):
        """
        刷新利率指标（LPR）到 `interest_rates` 基础表。
        """

        start_date = data_default_start_date
        end_date = latest_market_open_day

        try:
            df_lpr = self.api.shibor_lpr(
                start_date=start_date, 
                end_date=end_date,
                fields='date,1y,5y'
            )
        except Exception as e:
            logger.error(f"lpr fetch failed: {e}")
            return

        if df_lpr is None or df_lpr.empty:
            logger.info("lpr: no records returned")
            return

        records = []
        for _, r in df_lpr.iterrows():
            date_str = str(r.get('date') or r.get('DATE') or '').strip()
            lpr_1y = r.get('1y') if '1y' in r else r.get('lpr_1y') or r.get('LPR_1Y')
            lpr_5y = r.get('5y') if '5y' in r else r.get('lpr_5y') or r.get('LPR_5Y')

            records.append({
                'date': date_str,
                'LPR_1Y': TushareService.safe_to_float(lpr_1y),
                'LPR_5Y': TushareService.safe_to_float(lpr_5y),
            })

        if not records:
            return

        try:
            table = self.db.get_table_instance('lpr')
            table.replace(records, ['date'])
            logger.info(f"✅ 基准利率LPR 刷新完成: {len(records)} 条")
        except Exception as e:
            logger.error(f"❌ 基准利率LPR 更新失败: {e}")



    # ================================ Shibor ================================
    def renew_Shibor(self, latest_market_open_day: str = None):
        """
        刷新利率指标（Shibor）到 `interest_rates` 基础表。
        """
        
        start_date = data_default_start_date
        end_date = latest_market_open_day

        try:
            df_shibor = self.api.shibor(
                start_date=start_date,
                end_date=end_date,
                fields='date,on,1w,1m,3m,1y'
            )

            logger.info(f"shibor fetch success: {df_shibor}")
        except Exception as e:
            logger.error(f"shibor fetch failed: {e}")
            return

        records = []
        for _, r in df_shibor.iterrows():
            date_str = str(r.get('date') or r.get('DATE') or '').strip()
            shibor_on = r.get('on') if 'on' in r else r.get('ON')
            shibor_1w = r.get('1w') if '1w' in r else r.get('1W')
            shibor_1m = r.get('1m') if '1m' in r else r.get('1M')
            shibor_3m = r.get('3m') if '3m' in r else r.get('3M')
            shibor_1y = r.get('1y') if '1y' in r else r.get('1Y')
            records.append({
                'date': date_str,
                'one_night': TushareService.safe_to_float(shibor_on),
                'one_week': TushareService.safe_to_float(shibor_1w),
                'one_month': TushareService.safe_to_float(shibor_1m),
                'three_month': TushareService.safe_to_float(shibor_3m),
                'one_year': TushareService.safe_to_float(shibor_1y),
            })
        if not records:
            return
        
        try:
            table = self.db.get_table_instance('shibor')
            table.replace(records, ['date'])
            logger.info(f"✅ Shibor 刷新完成: {len(records)} 条")
        except Exception as e:
            logger.error(f"❌ Shibor 更新失败: {e}")


    # ================================ GDP ================================
    def renew_GDP(self, latest_market_open_day: str = None):
        start_quarter = TushareService.to_quarter(data_default_start_date)
        last_quarter = TushareService.to_quarter(latest_market_open_day)

        try:
            df_gdp = self.api.cn_gdp(
                start_m=start_quarter,
                end_m=last_quarter,
                fields='quarter,gdp,gdp_yoy,pi,pi_yoy,si,si_yoy,ti,ti_yoy'
            )
        except Exception as e:
            logger.error(f"gdp fetch failed: {e}")
            return

        if df_gdp is None or df_gdp.empty:
            logger.info("gdp: no records returned")
            return

        records = []
        for _, r in df_gdp.iterrows():
            quarter_str = str(r.get('quarter') or r.get('QUARTER') or '').strip()
            gdp = r.get('gdp') if 'gdp' in r else r.get('GDP')
            gdp_yoy = r.get('gdp_yoy') if 'gdp_yoy' in r else r.get('GDP_YOY')
            primary_industry = r.get('pi') if 'pi' in r else r.get('PI')
            primary_industry_yoy = r.get('pi_yoy') if 'pi_yoy' in r else r.get('PI_YOY')
            secondary_industry = r.get('si') if 'si' in r else r.get('SI')
            secondary_industry_yoy = r.get('si_yoy') if 'si_yoy' in r else r.get('SI_YOY')
            tertiary_industry = r.get('ti') if 'ti' in r else r.get('TI')
            tertiary_industry_yoy = r.get('ti_yoy') if 'ti_yoy' in r else r.get('TI_YOY')
            records.append({
                'quarter': quarter_str,
                'gdp': TushareService.safe_to_float(gdp),
                'gdp_yoy': TushareService.safe_to_float(gdp_yoy),
                'primary_industry': TushareService.safe_to_float(primary_industry),
                'primary_industry_yoy': TushareService.safe_to_float(primary_industry_yoy),
                'secondary_industry': TushareService.safe_to_float(secondary_industry),
                'secondary_industry_yoy': TushareService.safe_to_float(secondary_industry_yoy),
                'tertiary_industry': TushareService.safe_to_float(tertiary_industry),
                'tertiary_industry_yoy': TushareService.safe_to_float(tertiary_industry_yoy),
            })

        if not records:
            return

        try:
            table = self.db.get_table_instance('gdp')
            table.replace(records, ['quarter'])
            logger.info(f"✅ GDP 刷新完成: {len(records)} 条")
        except Exception as e:
            logger.error(f"❌ GDP 更新失败: {e}")


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
        from datetime import datetime, timedelta
        
        end_date = latest_market_open_day
        stock_indicator_ids = stock_index_indicators.keys()

        logger.info(f"📊 开始更新股票指数指标数据，目标日期: {end_date}")
        
        # 获取现有数据的最新日期
        most_recent_records = self.storage.get_most_recent_stock_index_indicator_record_dates()
        
        # 为每个股票指数检查是否需要更新
        for index_id in stock_indicator_ids:
            try:
                # 检查该指数是否有现有数据
                latest_date = most_recent_records.get(index_id, {}).get('daily')
                
                if latest_date:
                    # 有现有数据，检查是否需要更新
                    formatted_latest_date = datetime.strptime(latest_date, '%Y%m%d')
                    formatted_end_date = datetime.strptime(end_date, '%Y%m%d')
                    
                    if formatted_latest_date >= formatted_end_date:
                        logger.info(f"⏭️ {index_id} ({stock_index_indicators[index_id]}) 数据已是最新，跳过更新")
                        continue
                    
                    # 需要更新，从最新日期的下一天开始
                    start_date = (formatted_latest_date + timedelta(days=1)).strftime('%Y%m%d')
                    logger.info(f"🔄 更新 {index_id} ({stock_index_indicators[index_id]}) 从 {start_date} 到 {end_date}")
                else:
                    # 没有现有数据，从默认开始日期获取
                    start_date = data_default_start_date
                    logger.info(f"🔄 首次获取 {index_id} ({stock_index_indicators[index_id]}) 从 {start_date} 到 {end_date}")
                
                # 调用Tushare API获取指数日K线数据
                df_index_daily = self.api.index_daily(
                    ts_code=index_id,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df_index_daily is not None and not df_index_daily.empty:
                    # 保存到数据库
                    self.storage.batch_save_stock_index_indicator(df_index_daily, term='daily')
                    logger.info(f"✅ {index_id} 日K线数据更新完成，共 {len(df_index_daily)} 条记录")
                    
            except Exception as e:
                logger.error(f"❌ 获取 {index_id} 股票指数指标失败: {e}")
                continue
        
        logger.info("📊 股票指数指标数据更新完成")

    # ================================ stock index indicator weight ================================
    def renew_stock_index_indicator_weight(self, latest_market_open_day: str = None):
        """
        刷新股票指数指标权重数据
        获取主要股票指数的成分股权重数据
        """
        from datetime import datetime, timedelta
        
        end_date = latest_market_open_day
        stock_indicator_ids = stock_index_indicators.keys()

        logger.info(f"📊 开始更新股票指数指标权重数据，目标日期: {end_date}")
        # 获取现有数据的最新日期
        most_recent_records = self.storage.get_most_recent_stock_index_indicator_weight_record_dates()
        
        # 为每个股票指数检查是否需要更新
        for index_id in stock_indicator_ids:
            try:
                # 检查该指数是否有现有权重数据
                latest_date = most_recent_records.get(index_id)
                
                if latest_date:
                    # 有现有数据，检查是否需要更新
                    formatted_latest_date = datetime.strptime(latest_date, '%Y%m%d')
                    formatted_end_date = datetime.strptime(end_date, '%Y%m%d')
                    
                    if formatted_latest_date >= formatted_end_date:
                        logger.info(f"⏭️ {index_id} ({stock_index_indicators[index_id]}) 权重数据已是最新，跳过更新")
                        continue
                    
                    # 需要更新，从最新日期的下一天开始
                    start_date = (formatted_latest_date + timedelta(days=1)).strftime('%Y%m%d')
                    logger.info(f"🔄 更新 {index_id} ({stock_index_indicators[index_id]})")
                else:
                    # 没有现有数据，从默认开始日期获取
                    start_date = data_default_start_date
                    logger.info(f"🔄 首次获取 {index_id} ({stock_index_indicators[index_id]})")
                
                # 调用Tushare API获取指数权重数据
                df_index_weight = self.api.index_weight(
                    index_code=index_id,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df_index_weight is not None and not df_index_weight.empty:
                    # 保存到数据库
                    self.storage.batch_save_stock_index_indicator_weight(df_index_weight)
                    logger.info(f"✅ {index_id} 成分股权重数据更新完成，共 {len(df_index_weight)} 条记录")
            except Exception as e:
                logger.error(f"❌ 获取 {index_id} 股票指数指标权重失败: {e}")
                continue
        
        logger.info("📊 股票指数指标权重数据更新完成")

