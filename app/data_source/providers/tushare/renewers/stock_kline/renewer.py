"""
stock_kline 更新器

表结构：
- 主键：id (股票代码), term (K线周期), date (交易日期)
- 数据来源：daily (K线数据) + daily_basic (基本面数据)
- 特点：需要合并两个API，并处理daily_basic的缺失值（前向填充）
"""
from typing import Dict, List, Any
from loguru import logger
import pandas as pd
from ...base_renewer import BaseRenewer
from app.data_source.data_source_service import DataSourceService
from app.conf.conf import data_default_start_date


class StockKlineRenewer(BaseRenewer):
    """
    股票K线数据更新器
    
    业务逻辑：
    1. 支持3个term：daily（日线）、weekly（周线）、monthly（月线）
    2. 截止日期为latest_market_open_day的前一天
    3. K线数据：
       - 日线：调用 daily API
       - 周线：调用 weekly API
       - 月线：调用 monthly API
    4. 指标数据（pe、pb等）：
       - 所有term都调用 daily_basic API（只有日线指标）
       - 周线/月线需要找到对应日期的日线指标
    5. 指标纠错：前向填充缺失值
    
    重写方法：
    1. build_jobs - 为3个term分别构建任务
    2. should_execute_api - 根据term控制调用哪个K线API
    3. prepare_data_for_save - 合并K线和daily_basic，处理缺失值
    """
    
    def should_execute_api(self, api_config: Dict, previous_results: Dict) -> bool:
        """
        重写：根据当前job的term决定调用哪个K线API
        
        逻辑：
        - daily_basic: 总是调用（所有term都需要指标）
        - daily/weekly/monthly: 根据当前job的term只调用对应的一个
        
        示例：
        - term='daily' → 调用 daily + daily_basic
        - term='weekly' → 调用 weekly + daily_basic
        - term='monthly' → 调用 monthly + daily_basic
        """
        api_name = api_config.get('name')
        
        # daily_basic总是调用
        if api_name == 'daily_basic':
            return True
        
        # 获取当前job的term
        current_job = getattr(self, '_current_job', None) or {}
        current_term = current_job.get('term', 'daily')
        
        # 只调用匹配term的K线API
        return api_name == current_term
    
    def build_jobs(self, latest_market_open_day: str, stock_list: list = None, 
                   db_records: list = None) -> List[Dict]:
        """
        重写：为3个term（日/周/月）分别构建任务
        
        特殊逻辑：
        1. 截止日期为latest_market_open_day的前一天
        2. 日线：每天更新
        3. 周线：只有当形成新的周线时才更新（时间间隔>1周）
        4. 月线：只有当形成新的月线时才更新（时间间隔>1月）
        """
        jobs = []
        date_field = self.config['date']['field']
        
        # 截止日期为市场开放日的前一天
        # 因为latest_market_open_day当天数据可能还未更新
        from datetime import timedelta
        market_date_obj = DataSourceService.to_hyphen_date_type(latest_market_open_day)
        actual_end_date = (market_date_obj - timedelta(days=1)).strftime('%Y%m%d')
        
        try:
            primary_keys = self.db.get_table_primary_keys(self.config['table_name'])
        except ValueError as e:
            logger.error(f"❌ 构建任务失败: {e}")
            return []

        if not stock_list:
            return jobs

        # 为3个term分别构建任务
        terms_config = [
            {'term': 'daily', 'interval': 'day', 'min_gap': 1},
            {'term': 'weekly', 'interval': 'week', 'min_gap': 1},
            {'term': 'monthly', 'interval': 'month', 'min_gap': 1}
        ]
        
        for term_config in terms_config:
            term = term_config['term']
            interval = term_config['interval']
            min_gap = term_config['min_gap']
            
            # 为每个term构建jobs
            term_jobs = self._build_jobs_for_term(
                term, interval, min_gap, actual_end_date, 
                stock_list, db_records, date_field
            )
            jobs.extend(term_jobs)
        
        return jobs
    
    def _build_jobs_for_term(self, term: str, interval: str, min_gap: int,
                            end_date: str, stock_list: list, db_records: list,
                            date_field: str) -> List[Dict]:
        """
        为指定term构建jobs
        
        Args:
            term: K线周期（daily/weekly/monthly）
            interval: 时间间隔（day/week/month）
            min_gap: 最小时间间隔（用于判断是否需要更新）
            end_date: 截止日期
            stock_list: 股票列表
            db_records: 数据库记录
            date_field: 日期字段名
        """
        jobs = []
        
        if db_records:
            # 按id和term分组获取最新记录
            db_records_map = {}
            for record in db_records:
                if record.get('term') == term:
                    key = record.get('id')
                    if key not in db_records_map or record.get(date_field) > db_records_map[key].get(date_field):
                        db_records_map[key] = record
            
            for stock in stock_list:
                stock_id = stock.get('ts_code') or stock.get('id')
                
                if stock_id in db_records_map:
                    # 股票已存在，检查是否需要更新
                    latest_record = db_records_map[stock_id]
                    latest_date = latest_record[date_field]
                    
                    # 检查时间间隔是否足够（周线和月线需要足够的时间才形成新K线）
                    time_gap = DataSourceService.time_gap_by(interval, latest_date, end_date)
                    
                    if time_gap >= min_gap:
                        jobs.append({
                            'id': stock_id,
                            'ts_code': stock_id,
                            'term': term,
                            'start_date': DataSourceService.to_next(interval, latest_date),
                            'end_date': end_date,
                            '_log_vars': {
                                'stock_name': stock.get('name'),
                                'market': stock.get('market')
                            }
                        })
                else:
                    # 新股票，从默认日期开始
                    jobs.append({
                        'id': stock_id,
                        'ts_code': stock_id,
                        'term': term,
                        'start_date': data_default_start_date,
                        'end_date': end_date,
                        '_log_vars': {
                            'stock_name': stock.get('name'),
                            'market': stock.get('market')
                        }
                    })
        else:
            # 数据库无记录：全量拉取
            for stock in stock_list:
                stock_id = stock.get('ts_code') or stock.get('id')
                jobs.append({
                    'id': stock_id,
                    'ts_code': stock_id,
                    'term': term,
                    'start_date': data_default_start_date,
                    'end_date': end_date,
                    '_log_vars': {
                        'stock_name': stock.get('name'),
                        'market': stock.get('market')
                    }
                })
        
        return jobs
    
    def prepare_data_for_save(self, api_results: Dict[str, Any], job: Dict = None) -> Any:
        """
        重写：合并K线和daily_basic两个API，并处理缺失值
        
        处理逻辑：
        1. 根据term获取对应的K线数据（daily/weekly/monthly）
        2. 获取daily_basic数据（日线指标）
        3. LEFT JOIN合并，周线月线需要找对应日期的指标
        4. 前向填充缺失的指标值
        5. 添加term字段
        
        注意：
        - K线来自不同API（daily/weekly/monthly）
        - 指标都来自daily_basic（只有日线）
        - 周线月线需要匹配对应日期的日线指标
        """
        # 检查api_results是否为None
        if not api_results:
            logger.warning(f"⚠️  API结果为空")
            return None
        
        # 获取当前job的term
        term = job.get('term', 'daily') if job else 'daily'
        
        # 获取K线数据（根据term从对应的API获取）
        kline_data = api_results.get(term)  # daily/weekly/monthly
        basic_data = api_results.get('daily_basic')
        
        # 转换为DataFrame
        df_kline = self.to_df(kline_data)
        df_basic = self.to_df(basic_data)
        
        # 如果K线为空，直接返回
        if df_kline.empty:
            logger.info(f"ℹ️  {term} K线数据为空")
            return df_kline
        
        # 合并K线和daily_basic
        # 事务性原则：K线和daily_basic必须都成功，才能保存
        if df_basic.empty:
            # daily_basic失败，不保存数据，下次重试
            logger.warning(f"⚠️  daily_basic数据为空，跳过保存，等待下次重试")
            return None
        
        # 合并数据
        merged = self._merge_kline_and_basic(df_kline, df_basic, term)
        
        # 添加term字段
        merged['term'] = term
        
        return merged
    
    def _merge_kline_and_basic(self, df_kline: pd.DataFrame, df_basic: pd.DataFrame, term: str) -> pd.DataFrame:
        """
        合并K线和daily_basic数据，并处理缺失值
        
        Args:
            df_kline: K线数据（daily/weekly/monthly API，已映射为DB字段）
            df_basic: daily_basic数据（日线指标，已映射为DB字段）
            term: K线周期（daily/weekly/monthly）
            
        Returns:
            合并后的DataFrame
            
        逻辑：
        - 日线：direct LEFT JOIN（日期完全匹配）
        - 周线/月线：找最接近的日线指标（周/月最后一天对应的日线指标）
        """
        import pandas as pd
        
        # 1. 按date LEFT JOIN（保留所有K线数据）
        merged = pd.merge(df_kline, df_basic, on=['id', 'date'], how='left', suffixes=('', '_basic'))
        
        # 2. 对basic的字段进行前向填充（ffill）
        basic_columns = [
            'turnoverRate', 'freeTurnoverRate', 'volumeRatio',
            'pe', 'peTTM', 'pb', 'ps', 'psTTM',
            'dvRatio', 'dvTTM',
            'totalShare', 'floatShare', 'freeShare',
            'totalMarketValue', 'circMarketValue'
        ]
        
        # 按日期排序后前向填充（处理缺失值）
        merged = merged.sort_values('date')
        for col in basic_columns:
            if col in merged.columns:
                merged[col] = merged[col].ffill()
        
        # 3. 如果首行仍为空，用basic的首个非NaN值填充
        if not df_basic.empty and len(df_basic) > 0:
            for col in basic_columns:
                if col in df_basic.columns:
                    # 获取该列的第一个非NaN值
                    first_valid = df_basic[col].dropna().iloc[0] if not df_basic[col].dropna().empty else None
                    if first_valid is not None and not pd.isna(first_valid):
                        merged[col] = merged[col].fillna(first_valid)
        
        return merged


