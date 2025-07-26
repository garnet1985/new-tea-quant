"""
批量K线数据检查器
一次性获取所有股票的最新数据状态，生成更新任务列表
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from loguru import logger


class BatchKlineChecker:
    """批量K线数据检查器"""
    
    def __init__(self, storage):
        self.storage = storage
    
    def get_all_latest_kline_data(self) -> Dict[str, Dict[str, str]]:
        """
        一次性获取所有股票所有周期的最新数据日期
        返回格式: {code: {term: latest_date}}
        """
        try:
            # 使用SQL聚合查询获取所有股票所有周期的最新日期
            query = """
                SELECT code, term, MAX(date) as latest_date 
                FROM stock_kline 
                GROUP BY code, term
            """
            result = self.storage.stock_kline_table.execute_raw_query(query)
            
            # 转换为字典格式
            latest_data = {}
            for row in result:
                code = row['code']
                term = row['term']
                latest_date = row['latest_date']
                
                if code not in latest_data:
                    latest_data[code] = {}
                latest_data[code][term] = latest_date
            
            logger.info(f"获取到 {len(latest_data)} 只股票的最新数据状态")
            return latest_data
            
        except Exception as e:
            logger.error(f"获取最新数据状态失败: {e}")
            return {}
    
    def generate_update_jobs(self, stock_codes: List[str], terms: List[str], 
                           last_market_open_day: str) -> List[Dict[str, Any]]:
        """
        生成更新任务列表
        
        Args:
            stock_codes: 股票代码列表
            terms: 周期列表 ['daily', 'weekly', 'monthly']
            last_market_open_day: 最后交易日
            
        Returns:
            任务列表，每个任务包含 code, term, start_date, end_date
        """
        jobs = []
        latest_data = self.get_all_latest_kline_data()
        
        for code in stock_codes:
            for term in terms:
                job = self._create_job_for_stock_term(
                    code, term, last_market_open_day, latest_data
                )
                if job:
                    jobs.append(job)
        
        # 按优先级排序：日线 > 周线 > 月线
        term_priority = {'daily': 1, 'weekly': 2, 'monthly': 3}
        jobs.sort(key=lambda x: (term_priority.get(x['term'], 4), x['code']))
        
        logger.info(f"生成了 {len(jobs)} 个更新任务")
        return jobs
    
    def _create_job_for_stock_term(self, code: str, term: str, 
                                 last_market_open_day: str, 
                                 latest_data: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        为单个股票单个周期创建更新任务
        """
        from datetime import datetime, timedelta
        
        # 获取该股票该周期的最新数据日期
        latest_date = latest_data.get(code, {}).get(term)
        
        if not latest_date:
            # 没有数据，需要获取全部数据
            return {
                'code': code,
                'term': term,
                'start_date': None,  # 从最早开始
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
                    'term': term,
                    'start_date': start_date,
                    'end_date': last_market_open_day,
                    'reason': 'monthly_update'
                }
        
        # 不需要更新
        return None
    
    def get_job_statistics(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取任务统计信息"""
        stats = {
            'total_jobs': len(jobs),
            'by_term': {},
            'by_reason': {},
            'estimated_data_points': 0
        }
        
        for job in jobs:
            term = job['term']
            reason = job['reason']
            
            # 按周期统计
            if term not in stats['by_term']:
                stats['by_term'][term] = 0
            stats['by_term'][term] += 1
            
            # 按原因统计
            if reason not in stats['by_reason']:
                stats['by_reason'][reason] = 0
            stats['by_reason'][reason] += 1
        
        return stats 