import pprint
import tushare as ts
from loguru import logger
from utils.worker import FuturesWorker, ThreadExecutionMode
from app.data_source.providers.tushare.main_settings import auth_token_file
from app.data_source.providers.tushare.main_service import TushareService
from app.data_source.providers.tushare.main_storage import TushareStorage
import warnings
from datetime import datetime, date
import time


# 抑制tushare库的FutureWarning
warnings.filterwarnings('ignore', category=FutureWarning, module='tushare')

class Tushare:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.db = connected_db
        self.storage = TushareStorage(connected_db)


        self.is_verbose = is_verbose

        self.use_token();
        self.api = ts.pro_api()
        
        # 添加Tushare K线数据API频率限制
        self.kline_api_count = 0
        self.kline_api_last_time = 0
        self.kline_api_max_per_minute = 780  # Tushare 有 800 次每分钟限制
        
        # 添加线程锁，确保多线程环境下的限流安全
        import threading
        self.kline_api_lock = threading.Lock()
        # 进度统计
        self.kline_total_jobs = 0
        self.kline_completed_jobs = 0
        self.kline_progress_lock = threading.Lock()

        # 线程局部 DB（用于每个工作线程独立复用同一个 DatabaseManager 与 Storage）
        self._thread_local = threading.local()
        self._thread_dbs = []
        self._thread_dbs_lock = threading.Lock()

    
    # ================================ auth related ================================
    def get_token(self):
        try:
            with open(auth_token_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Token file not found at: {auth_token_file}. Please create file with token string inside.")

    def use_token(self):
        ts.set_token(self.get_token())

    # ================================ k line api rate limit ================================
    def _k_line_api_rate_limit(self):
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
        # 初始化进度
        self.kline_total_jobs = total_stocks
        self.kline_completed_jobs = 0
        
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
            with self.kline_progress_lock:
                self.kline_completed_jobs += 1
                progress = (self.kline_completed_jobs / self.kline_total_jobs * 100) if self.kline_total_jobs else 100
                logger.info(f"📈 K线更新进度: {self.kline_completed_jobs}/{self.kline_total_jobs} ({progress:.1f}%) 完成; 当前股票: {stock_key}, 状态: {result['status']}")
            return result
                
        except Exception as e:
            logger.error(f"❌ 处理股票 {stock_key} 失败: {e}")
            # 失败也计入进度
            with self.kline_progress_lock:
                self.kline_completed_jobs += 1
                progress = (self.kline_completed_jobs / self.kline_total_jobs * 100) if self.kline_total_jobs else 100
                logger.info(f"📈 K线更新进度: {self.kline_completed_jobs}/{self.kline_total_jobs} ({progress:.1f}%) 完成; 当前股票: {stock_key}, 状态: failed")
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

        # 统一比较为日期类型
        def _to_date(value):
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                v = value.strip()
                # 常见格式：YYYYMMDD 或 YYYY-MM-DD 或 YYYY/MM/DD
                for fmt in ('%Y%m%d', '%Y-%m-%d', '%Y/%m/%d'):
                    try:
                        return datetime.strptime(v, fmt).date()
                    except ValueError:
                        continue
            # 无法解析则返回 None
            return None

        last_dt = _to_date(last_renew_time)
        latest_dt = _to_date(latest_market_open_day)

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
        from datetime import datetime
        import math
        from app.data_source.providers.conf.conf import data_default_start_date

        # 统一起止区间（与K线一致）：若未显式传入，则用配置默认起点 → 最新交易日
        def to_yyyymm(d: str) -> str:
            d = (d or '').strip()
            if not d:
                return ''
            # 支持 YYYYMMDD / YYYY-MM-DD / YYYY/MM/DD / YYYYMM
            for fmt in ('%Y%m%d', '%Y-%m-%d', '%Y/%m/%d', '%Y%m'):
                try:
                    return datetime.strptime(d, fmt).strftime('%Y%m')
                except ValueError:
                    continue
            return ''

        start_m = to_yyyymm(data_default_start_date)
        end_m = to_yyyymm(latest_market_open_day) or datetime.now().strftime('%Y%m')

        def safe_to_float(x, default=0.0):
            try:
                if x is None or (isinstance(x, float) and math.isnan(x)):
                    return default
                return float(x)
            except Exception:
                return default

        # month -> row dict
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
                    row['M0'] = safe_to_float(r.get('m0'))
                    row['M0_yoy'] = safe_to_float(r.get('m0_yoy'))
                    row['M0_mom'] = safe_to_float(r.get('m0_mom'))
                    row['M1'] = safe_to_float(r.get('m1'))
                    row['M1_yoy'] = safe_to_float(r.get('m1_yoy'))
                    row['M1_mom'] = safe_to_float(r.get('m1_mom'))
                    row['M2'] = safe_to_float(r.get('m2'))
                    row['M2_yoy'] = safe_to_float(r.get('m2_yoy'))
                    row['M2_mom'] = safe_to_float(r.get('m2_mom'))
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
                    row['CPI'] = safe_to_float(r.get('nt_val'))
                    row['CPI_yoy'] = safe_to_float(r.get('nt_yoy'))
                    row['CPI_mom'] = safe_to_float(r.get('nt_mom'))
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

                    row['PPI'] = safe_to_float(r.get('ppi_accu'))
                    row['PPI_yoy'] = safe_to_float(r.get('ppi_yoy'))
                    row['PPI_mom'] = safe_to_float(r.get('ppi_mom'))
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
                    row['PMI'] = safe_to_float(r.get('pmi010000') or r.get('PMI010000'))
                    row['PMI_l_scale'] = safe_to_float(r.get('pmi010100') or r.get('PMI010100'))
                    row['PMI_m_scale'] = safe_to_float(r.get('pmi010200') or r.get('PMI010200'))
                    row['PMI_s_scale'] = safe_to_float(r.get('pmi010300') or r.get('PMI010300'))
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
            logger.info("price_indexes: no records to update")
            return

        try:
            table = self.db.get_table_instance('price_indexes')
            table.replace(records, ['id', 'date'])
            logger.info(f"✅ price_indexes 刷新完成: {len(records)} 条")
        except Exception as e:
            logger.error(f"❌ price_indexes 刷新失败: {e}")

    