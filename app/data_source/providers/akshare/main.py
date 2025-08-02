from app.data_source.providers.akshare.main_service import AKShareService
from app.data_source.providers.akshare.main_storage import AKShareStorage
from utils.worker import FuturesWorker
from loguru import logger
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class AKShare:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.storage = AKShareStorage(connected_db)
        self.service = AKShareService(is_verbose)
        self.is_verbose = is_verbose

    def renew_stock_K_line_factors(self, stock_index: list = None, force_update: bool = False):
        if self.is_verbose:
            logger.info(f"Starting stock K-line factors renewal for {len(stock_index) if stock_index else 'all'} stocks")
        
        if not force_update and not self.storage.should_update_adj_factors():
            if self.is_verbose:
                logger.info("距离上次更新未满1天，跳过更新")
            return False
        
        return self._daily_update(stock_index)

    def _daily_update(self, stock_index: list) -> bool:
        if self.is_verbose:
            logger.info("每日更新，获取所有股票的最新复权因子")
        
        # 获取最近5天的数据来计算最新因子
        start_date, end_date = self.service.get_recent_date_range(5)
        jobs = self._build_jobs(stock_index, start_date, end_date)
        
        success = self._execute_jobs(jobs)
        if success:
            self.storage.update_last_update_time()
        
        return success

    def _build_jobs(self, stock_index: list, start_date: str, end_date: str) -> List[Dict]:
        jobs = []
        for stock_info in stock_index:
            jobs.append({
                'stock_code': stock_info['code'],
                'market': stock_info['market'],
                'start_date': start_date,
                'end_date': end_date
            })
        return jobs

    def _execute_jobs(self, jobs: List[Dict]) -> bool:
        worker = FuturesWorker(max_workers=5, is_verbose=self.is_verbose)
        worker.set_job_executor(self._process_single_stock)
        
        job_list = []
        for i, job in enumerate(jobs):
            job_list.append({
                'id': f"job_{i}",
                'data': job
            })
        
        stats = worker.run_jobs(job_list)
        results = worker.get_results()
        
        success_count = sum(1 for result in results if result.status.value == 'completed')
        success_rate = success_count / len(jobs) if jobs else 0
        
        if self.is_verbose:
            logger.info(f"Batch execution completed: {success_count}/{len(jobs)} jobs successful ({success_rate:.1%})")
        
        return success_rate >= 0.8

    def _process_single_stock(self, job: Dict) -> Dict:
        stock_code = job['stock_code']
        market = job['market']
        start_date = job['start_date']
        end_date = job['end_date']
        
        if self.is_verbose:
            logger.info(f"Processing {stock_code}.{market}")
        
        merged_data = self.service.fetch_stock_factors(stock_code, start_date, end_date)
        
        if merged_data is None or merged_data.empty:
            return {'status': 'failed', 'reason': 'no_data'}
        
        factors_data = self.service.prepare_factor_data(merged_data, stock_code, market)
        success = self.storage.batch_upsert_adj_factors(factors_data)
        
        return {'status': 'completed' if success else 'failed'}

    def force_update_adj_factors(self, stock_index: list = None):
        if self.is_verbose:
            logger.info("Force updating adj factors")
        return self.renew_stock_K_line_factors(stock_index, force_update=True)

    def check_update_status(self) -> Dict:
        return self.storage.get_update_status_info()

    def get_update_info(self) -> str:
        status = self.check_update_status()
        if status['status'] == 'never_updated':
            return "从未更新过复权因子"
        elif status['status'] == 'needs_update':
            return f"需要更新，距离上次更新已过去 {status['days_since_update']} 天"
        else:
            return f"无需更新，距离上次更新仅过去 {status['days_since_update']} 天"


