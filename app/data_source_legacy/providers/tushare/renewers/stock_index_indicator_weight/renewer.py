"""
股指成分股权重更新器

使用 Tushare 的 index_weight 接口获取指数成分股权重数据
"""

from typing import Dict, List, Optional, Any
from loguru import logger
from app.data_source.data_source_service import DataSourceService
from ...base_renewer import BaseRenewer


class StockIndexIndicatorWeightRenewer(BaseRenewer):
    """
    股指成分股权重更新器
    
    特点：
    - 为每个指数生成一个job
    - 单API，简单mapping
    - 使用 index_list 而不是 stock_list
    """
    
    def build_jobs(self, latest_market_open_day: str, stock_list: list = None, 
                   db_records: list = None) -> List[Dict]:
        """
        构建指数权重更新任务
        
        为每个指数生成一个job
        使用 index_list 而不是 stock_list
        
        Returns:
            List[Dict]: [{id, start_date, end_date, _log_vars}, ...]
        """
        from app.conf.conf import data_default_start_date
        
        jobs = []
        index_list = self.config.get('index_list', [])
        
        # 获取数据库中的最新记录（按 id 分组）
        table = self.db.get_table_instance(self.config['table_name'])
        
        # 只在需要时加载历史记录
        if db_records is None:
            renew_mode = self.config.get('renew_mode', 'incremental').lower()
            if renew_mode in ['incremental', 'upsert']:
                db_records = table.load_latest_records()
        
        # 构建 db_records_map: {id: latest_record}
        db_map = {}
        if db_records:
            for record in db_records:
                db_map[record['id']] = record
        
        # 计算实际结束日期（前一个交易日）
        actual_end_date = DataSourceService.to_previous_day(latest_market_open_day)
        
        # 为每个指数生成任务
        for index_info in index_list:
            index_id = index_info['id']
            index_name = index_info.get('name', index_id)
            
            if index_id in db_map:
                # 有历史记录，检查是否需要更新
                latest_record = db_map[index_id]
                latest_date = latest_record['date']
                
                # 计算时间gap（指数成分股不常变化，至少1个月才更新）
                time_gap = DataSourceService.time_gap_by('month', latest_date, actual_end_date)
                
                if time_gap >= 1:
                    # 需要更新
                    start_date = DataSourceService.to_next('day', latest_date)
                    
                    jobs.append({
                        'id': index_id,
                        'start_date': start_date,
                        'end_date': actual_end_date,
                        '_log_vars': {
                            'index_name': index_name,
                            'id': index_id
                        }
                    })
            else:
                # 无历史记录，全量拉取
                jobs.append({
                    'id': index_id,
                    'start_date': data_default_start_date,
                    'end_date': actual_end_date,
                    '_log_vars': {
                        'index_name': index_name,
                        'id': index_id
                    }
                })
        
        return jobs
    
    def prepare_data_for_save(self, api_results: Dict[str, Any], job: Dict = None) -> Any:
        """
        准备数据保存
        
        需要添加 id 字段（从job中获取）
        """
        if not api_results:
            return None
        
        # 获取权重数据
        weight_data = api_results.get('index_weight')
        if weight_data is None:
            return None
        
        import pandas as pd
        df = pd.DataFrame(weight_data) if not isinstance(weight_data, pd.DataFrame) else weight_data
        
        if df.empty:
            logger.warning("⚠️  指数权重数据为空")
            return None
        
        # 添加指数ID（从job中获取）
        df['id'] = job.get('id')
        
        logger.info(f"📊 权重数据：{len(df)} 条记录（成分股数量）")
        
        return df

