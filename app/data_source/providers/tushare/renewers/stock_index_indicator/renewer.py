"""
股指指标更新器

使用 Tushare 的 index_daily/weekly/monthly 和 index_dailybasic 接口
获取指数的K线数据和每日指标
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from loguru import logger
from app.data_source.data_source_service import DataSourceService
from ...base_renewer import BaseRenewer


class StockIndexIndicatorRenewer(BaseRenewer):
    """
    股指指标更新器
    
    特点：
    - 类似 stock_kline，处理 daily, weekly, monthly 三个term
    - 每个指数×每个term = 一个job
    - 需要合并 index_xxx 和 index_dailybasic
    """
    
    def build_jobs(self, latest_market_open_day: str, stock_list: list = None, 
                   db_records: list = None) -> List[Dict]:
        """
        构建指数更新任务
        
        为每个指数的每个term生成一个job
        使用 index_list 而不是 stock_list
        
        Returns:
            List[Dict]: [{id, term, start_date, end_date, _log_vars}, ...]
        """
        from app.conf.conf import data_default_start_date
        
        jobs = []
        index_list = self.config.get('index_list', [])
        
        # 获取数据库中的最新记录（按 id+term 分组）
        table = self.db.get_table_instance(self.config['table_name'])
        
        # 只在需要时加载历史记录
        if db_records is None:
            renew_mode = self.config.get('renew_mode', 'incremental').lower()
            if renew_mode in ['incremental', 'upsert']:
                db_records = table.load_latest_records()
        
        # 构建 db_records_map: {id_term: latest_record}
        db_map = {}
        if db_records:
            for record in db_records:
                key = f"{record['id']}_{record.get('term', '')}"
                db_map[key] = record
        
        # 计算实际结束日期（前一个交易日）
        from datetime import datetime, timedelta
        market_date_obj = datetime.strptime(latest_market_open_day, '%Y%m%d')
        actual_end_date = (market_date_obj - timedelta(days=1)).strftime('%Y%m%d')
        
        # 为每个指数×每个term生成任务
        terms_config = [
            {'term': 'daily', 'interval': 'day', 'min_gap': 1, 'end_date': actual_end_date},
            {'term': 'weekly', 'interval': 'week', 'min_gap': 1, 
             'end_date': DataSourceService.get_previous_week_end(latest_market_open_day)},
            {'term': 'monthly', 'interval': 'month', 'min_gap': 1,
             'end_date': DataSourceService.get_previous_month_end(latest_market_open_day)}
        ]
        
        for index_info in index_list:
            index_id = index_info['id']
            index_name = index_info.get('name', index_id)
            
            for term_cfg in terms_config:
                term = term_cfg['term']
                interval = term_cfg['interval']
                min_gap = term_cfg['min_gap']
                end_date = term_cfg['end_date']
                
                key = f"{index_id}_{term}"
                
                if key in db_map:
                    # 有历史记录，检查是否需要更新
                    latest_record = db_map[key]
                    latest_date = latest_record['date']
                    
                    # 计算时间gap
                    time_gap = DataSourceService.time_gap_by(interval, latest_date, end_date)
                    
                    if time_gap >= min_gap:
                        # 需要更新
                        start_date = DataSourceService.to_next('day', latest_date)
                        
                        jobs.append({
                            'id': index_id,
                            'term': term,
                            'start_date': start_date,
                            'end_date': end_date,
                            '_log_vars': {
                                'index_name': index_name,
                                'id': index_id,
                                'term': term
                            }
                        })
                else:
                    # 无历史记录，全量拉取
                    jobs.append({
                        'id': index_id,
                        'term': term,
                        'start_date': data_default_start_date,
                        'end_date': end_date,
                        '_log_vars': {
                            'index_name': index_name,
                            'id': index_id,
                            'term': term
                        }
                    })
        
        return jobs
    
    def should_execute_api(self, api: Dict, api_results: Dict[str, Any] = None) -> bool:
        """
        根据当前job的term决定执行哪个K线API
        
        - daily term → 执行 index_daily
        - weekly term → 执行 index_weekly
        - monthly term → 执行 index_monthly
        """
        current_job = getattr(self, '_current_job', None) or {}
        term = current_job.get('term', 'daily')
        api_name = api.get('name', '')
        
        # 根据term选择对应的K线API
        if term == 'daily' and api_name == 'index_daily':
            return True
        elif term == 'weekly' and api_name == 'index_weekly':
            return True
        elif term == 'monthly' and api_name == 'index_monthly':
            return True
        
        return False
    
    def _request_apis(self, job: Dict) -> Dict[str, Any]:
        """
        动态配置APIs并执行
        
        根据job的term，动态构建API配置
        只需要K线数据，不需要dailybasic
        """
        term = job.get('term', 'daily')
        
        # 动态构建API配置（只包含K线API）
        apis = [
            {
                'name': 'index_daily',
                'method': 'index_daily',
                'params': {
                    'ts_code': '{id}',
                    'start_date': '{start_date}',
                    'end_date': '{end_date}'
                },
                'mapping': {
                    'date': 'trade_date',
                    'open': 'open',
                    'close': 'close',
                    'highest': 'high',
                    'lowest': 'low',
                    'price_change_delta': 'change',
                    'price_change_rate_delta': 'pct_chg',
                    'pre_close': 'pre_close',
                    'volume': 'vol',
                    'amount': 'amount'
                }
            },
            {
                'name': 'index_weekly',
                'method': 'index_weekly',
                'params': {
                    'ts_code': '{id}',
                    'start_date': '{start_date}',
                    'end_date': '{end_date}'
                },
                'mapping': {
                    'date': 'trade_date',
                    'open': 'open',
                    'close': 'close',
                    'highest': 'high',
                    'lowest': 'low',
                    'price_change_delta': 'change',
                    'price_change_rate_delta': 'pct_chg',
                    'pre_close': 'pre_close',
                    'volume': 'vol',
                    'amount': 'amount'
                }
            },
            {
                'name': 'index_monthly',
                'method': 'index_monthly',
                'params': {
                    'ts_code': '{id}',
                    'start_date': '{start_date}',
                    'end_date': '{end_date}'
                },
                'mapping': {
                    'date': 'trade_date',
                    'open': 'open',
                    'close': 'close',
                    'highest': 'high',
                    'lowest': 'low',
                    'price_change_delta': 'change',
                    'price_change_rate_delta': 'pct_chg',
                    'pre_close': 'pre_close',
                    'volume': 'vol',
                    'amount': 'amount'
                }
            }
        ]
        
        # 临时存储到config中（供BaseRenewer使用）
        self.config['apis'] = apis
        
        # 调用父类方法
        return super()._request_apis(job)
    
    def prepare_data_for_save(self, api_results: Dict[str, Any], job: Dict = None) -> Any:
        """
        准备指数K线数据保存
        
        只需要处理K线数据，添加 id 和 term 字段
        """
        if not api_results:
            return None
        
        term = job.get('term', 'daily') if job else 'daily'
        
        # 获取K线数据（根据term选择正确的API结果）
        df_kline = None
        
        for api_name in ['index_daily', 'index_weekly', 'index_monthly']:
            if api_name in api_results and api_results[api_name] is not None:
                df = api_results[api_name]
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df_kline = df
                    break
        
        if df_kline is None or df_kline.empty:
            logger.warning(f"⚠️  指数K线数据为空 [{term}]")
            return None
        
        # 添加主键字段
        df_kline['id'] = job.get('id')
        df_kline['term'] = term
        
        logger.info(f"📊 指数K线数据：{len(df_kline)} 条记录")
        
        return df_kline

