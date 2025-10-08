"""
Shibor更新器
"""

from typing import Dict, List, Any
from loguru import logger
from ...base_renewer import BaseRenewer


class ShiborRenewer(BaseRenewer):
    """Shibor更新器 - 简单模式"""
    
    def combine_apis_data(self, api_results: Dict[str, Any]) -> Any:
        """合并API数据并应用字段映射"""
        if len(api_results) == 1:
            result = list(api_results.values())[0]
            
            if result is None or (hasattr(result, 'empty') and result.empty):
                logger.info("ℹ️ Shibor 没有新数据")
                return result
            
            # 应用字段映射
            api_config = self.config.get('apis', [])[0]
            mapping = api_config.get('mapping', {})
            
            if mapping:
                logger.info(f"📊 应用字段映射: {mapping}")
                result = result.rename(columns=mapping)
                
                # 只保留数据库表中存在的字段
                db_fields = ['date', 'one_night', 'one_week', 'one_month', 'three_month', 'one_year']
                available_fields = [col for col in db_fields if col in result.columns]
                result = result[available_fields]
                
                logger.info(f"📊 保留字段: {available_fields}")
                
                # 过滤掉数据库中已存在的日期数据
                if len(result) > 0:
                    # 获取数据库中已存在的日期
                    existing_dates_query = '''
                    SELECT date FROM shibor 
                    ORDER BY date DESC
                    '''
                    existing_records = self.db.execute_sync_query(existing_dates_query)
                    existing_dates = {row['date'] for row in existing_records}
                    
                    # 过滤掉已存在的日期
                    original_count = len(result)
                    result = result[~result['date'].isin(existing_dates)]
                    filtered_count = len(result)
                    
                    if original_count > filtered_count:
                        logger.info(f"📊 过滤掉 {original_count - filtered_count} 条已存在的日期数据，剩余 {filtered_count} 条新数据")
                    
                    if filtered_count == 0:
                        logger.info(f"ℹ️ 所有数据都已存在，跳过保存")
                        return None
            
            return result
        
        # 多个API结果的情况（Shibor通常只有一个API）
        return None
