"""
LPR利率更新器 - 增量存储，只在利率值变化时存储
"""

from typing import Dict, List, Any, Optional
from loguru import logger
from ...base_renewer import BaseRenewer


class LPRRenewer(BaseRenewer):
    """LPR利率更新器 - 增量存储逻辑"""
    
    def should_renew(self, start_date: str = None, end_date: str = None) -> Optional[str]:
        """判断是否需要更新LPR数据"""
        # LPR数据需要定期检查是否有新变化，总是返回需要更新的开始日期
        return start_date or "20200101"
    
    def build_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        """构建LPR更新任务"""
        jobs = []
        
        try:
            # 获取最新的LPR数据用于对比
            latest_lpr = self._get_latest_lpr_data()
            
            # 创建任务获取最新数据
            jobs.append({
                'start_date': start_date,
                'end_date': end_date,
                'api_method': 'shibor_lpr',
                'api_params': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'fields': 'date,1y,5y'
                },
                'latest_lpr': latest_lpr  # 传递最新数据用于对比
            })
            
            logger.info(f"📊 构建了 {len(jobs)} 个LPR更新任务")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ 构建LPR任务失败: {e}")
            return []
    
    def process_data_before_save(self, data: Any) -> Any:
        """处理LPR数据，确保数值字段有合适的默认值"""
        if data is None:
            return data
        
        # 检查 DataFrame 是否为空
        if hasattr(data, 'empty') and data.empty:
            logger.info("📊 LPR API返回空数据，跳过存储")
            return data
        
        # 将 DataFrame 转换为字典列表
        if hasattr(data, 'to_dict'):
            data_list = data.to_dict('records')
        elif isinstance(data, list):
            data_list = data
        else:
            return data
        
        # 处理每条记录，确保数值字段有默认值
        for record in data_list:
            # 处理NaN值，提供默认值
            if record.get('LPR_1Y') is None or str(record.get('LPR_1Y')).lower() == 'nan':
                record['LPR_1Y'] = 0.0
            if record.get('LPR_5Y') is None or str(record.get('LPR_5Y')).lower() == 'nan':
                record['LPR_5Y'] = 0.0
        
        logger.info(f"📊 LPR增量更新: 准备存储 {len(data_list)} 条记录")
        return data_list
