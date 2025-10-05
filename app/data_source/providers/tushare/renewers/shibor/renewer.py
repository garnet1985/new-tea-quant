"""
Shibor更新器
"""

from typing import Dict, List, Any
from loguru import logger
from ...base_renewer import BaseRenewer


class ShiborRenewer(BaseRenewer):
    """Shibor更新器 - 使用默认实现"""
    
    def build_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        """构建Shibor更新任务"""
        jobs = []
        
        try:
            jobs.append({
                'start_date': start_date,
                'end_date': end_date,
                'api_method': 'shibor',
                'api_params': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            })
            
            logger.info(f"📊 构建了 {len(jobs)} 个Shibor更新任务")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ 构建Shibor任务失败: {e}")
            return []
