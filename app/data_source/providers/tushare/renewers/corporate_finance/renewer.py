"""
企业财务更新器
"""

from typing import Dict, List, Any
from loguru import logger
from ...base_renewer import BaseRenewer


class CorporateFinanceRenewer(BaseRenewer):
    """企业财务更新器 - 使用默认实现"""
    
    def build_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        """构建企业财务更新任务"""
        jobs = []
        
        try:
            # 获取股票列表
            stock_index = self.storage.load_stock_index()
            if not stock_index:
                logger.warning("❌ 没有股票数据，无法构建企业财务更新任务")
                return []
            
            # 为每只股票创建任务
            for stock in stock_index:
                stock_id = stock['id']
                jobs.append({
                    'ts_code': stock_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'api_method': 'income',
                    'api_params': {
                        'ts_code': stock_id,
                        'start_date': start_date,
                        'end_date': end_date,
                        'fields': 'ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,revenue,total_cogs'
                    }
                })
                
                # 添加资产负债表任务
                jobs.append({
                    'ts_code': stock_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'api_method': 'balancesheet',
                    'api_params': {
                        'ts_code': stock_id,
                        'start_date': start_date,
                        'end_date': end_date,
                        'fields': 'ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,total_share,float_share'
                    }
                })
            
            logger.info(f"📊 构建了 {len(jobs)} 个企业财务更新任务")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ 构建企业财务任务失败: {e}")
            return []
