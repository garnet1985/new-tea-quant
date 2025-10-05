"""
股票基本信息更新器
"""

from typing import Dict, List, Any
from loguru import logger
from ...base_renewer import BaseRenewer


class StockIndexRenewer(BaseRenewer):
    """股票基本信息更新器 - 实现原来的renew_index逻辑"""
    
    def build_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        """构建任务（股票基本信息不需要复杂的任务构建）"""
        return []  # 股票基本信息是单次API调用，不需要任务构建
    
    def renew(self, latest_market_open_day: str = None):
        """
        重写renew方法，实现原来的renew_index逻辑
        """
        logger.info(f"🔄 开始更新股票基本信息")
        
        try:
            # 1. 获取API数据
            api_data = self._fetch_api_data()
            if not api_data:
                logger.warning("⚠️ API返回空数据")
                return False
            
            # 2. 转换数据格式
            formatted_data = self._format_data(api_data)
            
            # 3. 使用原来的renew_index逻辑
            table_instance = self.db.get_table_instance('stock_index')
            if hasattr(table_instance, 'renew_index'):
                table_instance.renew_index(formatted_data)
                logger.info(f"✅ 股票基本信息更新完成，处理了 {len(formatted_data)} 只股票")
                return len(formatted_data)
            else:
                logger.error("❌ stock_index表没有renew_index方法")
                return False
                
        except Exception as e:
            logger.error(f"❌ 股票基本信息更新失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def _fetch_api_data(self) -> List[Dict]:
        """获取API数据"""
        try:
            api_config = self.config['apis'][0]  # 取第一个API配置
            api_method_name = api_config['method']
            api_params = api_config['params']
            
            # 获取API方法
            api_method = getattr(self.api, api_method_name)
            
            # 调用API
            result = api_method(**api_params)
            
            if result is None or (hasattr(result, 'empty') and result.empty):
                return []
            
            # 转换为字典列表
            if hasattr(result, 'to_dict'):
                return result.to_dict('records')
            else:
                return list(result)
                
        except Exception as e:
            logger.error(f"❌ 获取API数据失败: {e}")
            return []
    
    def _format_data(self, api_data: List[Dict]) -> List[Dict]:
        """格式化数据"""
        formatted_data = []
        
        for item in api_data:
            # 应用字段映射
            mapped_item = {}
            mapping = self.config['apis'][0]['mapping']
            
            for db_field, mapping_func in mapping.items():
                if callable(mapping_func):
                    mapped_item[db_field] = mapping_func(item)
                else:
                    mapped_item[db_field] = item.get(mapping_func)
            
            # 验证必填字段
            if mapped_item.get('id') and mapped_item.get('name'):
                formatted_data.append(mapped_item)
        
        return formatted_data
