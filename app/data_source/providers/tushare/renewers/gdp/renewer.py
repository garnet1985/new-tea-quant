"""
GDP更新器
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger
from ...base_renewer import BaseRenewer


class GDPRenewer(BaseRenewer):
    """GDP更新器 - 简单模式"""
    
    def should_renew(self, start_date: str = None, end_date: str = None) -> Optional[str]:
        """自定义 should_renew 逻辑"""
        table_name = self.config['table_name']
        
        # 检查数据库中最新季度
        try:
            latest_quarter_query = '''
            SELECT quarter FROM gdp 
            ORDER BY quarter DESC 
            LIMIT 1
            '''
            latest_records = self.db.execute_sync_query(latest_quarter_query)
            
            if not latest_records:
                # 数据库为空，从默认日期开始
                return "20080101"
            
            latest_quarter = latest_records[0]['quarter']
            
            # 将季度转换为下一个季度的开始日期
            year = int(latest_quarter[:4])
            quarter = int(latest_quarter[5])
            
            if quarter == 1:
                next_quarter_start = f"{year}0401"  # Q2 开始
            elif quarter == 2:
                next_quarter_start = f"{year}0701"  # Q3 开始
            elif quarter == 3:
                next_quarter_start = f"{year}1001"  # Q4 开始
            elif quarter == 4:
                next_quarter_start = f"{year+1}0101"  # 下一年 Q1 开始
            else:
                next_quarter_start = f"{year}0101"
            
            # 如果下一个季度开始日期小于等于结束日期，则需要更新
            if next_quarter_start <= (end_date or "20241231"):
                return next_quarter_start
            
            return None
            
        except Exception as e:
            logger.warning(f"❌ 检查GDP最新季度失败: {e}")
            return "20080101"
    
    def renew(self, latest_market_open_day: str = None) -> bool:
        """更新GDP数据（简单模式）"""
        try:
            logger.info(f"🔄 开始更新 {self.config['table_name']}，参数: latest_market_open_day={latest_market_open_day}")
            
            # 检查是否需要更新
            should_renew_date = self.should_renew(latest_market_open_day, latest_market_open_day)
            logger.info(f"🔍 should_renew 返回: {should_renew_date}")
            
            if should_renew_date:
                start_date = should_renew_date
                end_date = latest_market_open_day or datetime.now().strftime('%Y%m%d')
                logger.info(f"📅 需要从 {start_date} 开始更新到 {end_date}")
                
                # 确保日期范围有效
                if start_date > end_date:
                    logger.info(f"ℹ️ 开始日期 {start_date} 大于结束日期 {end_date}，跳过更新")
                    return True
            else:
                logger.info(f"ℹ️ {self.config['table_name']} 数据已是最新，跳过更新")
                return True
            
            # 调用API获取数据
            api_config = self.config.get('apis', [])[0]
            api_method = getattr(self.api, api_config['method'])
            
            try:
                # 准备API参数
                api_params = {
                    'start_date': start_date,
                    'end_date': end_date
                }
                
                logger.info(f"📊 调用API: {api_config['method']}")
                result = api_method(**api_params)
                
                if result is None or (hasattr(result, 'empty') and result.empty):
                    logger.info(f"ℹ️ {self.config['table_name']} 没有新数据")
                    return True
                
                
                # 应用字段映射
                mapping = api_config.get('mapping', {})
                if mapping:
                    # 重命名列
                    result = result.rename(columns=mapping)
                
                # 过滤掉数据库中已存在的季度数据
                if len(result) > 0:
                    # 获取数据库中已存在的季度
                    existing_quarters_query = '''
                    SELECT quarter FROM gdp 
                    ORDER BY quarter DESC
                    '''
                    existing_records = self.db.execute_sync_query(existing_quarters_query)
                    existing_quarters = {row['quarter'] for row in existing_records}
                    
                    # 过滤掉已存在的季度
                    original_count = len(result)
                    result = result[~result['quarter'].isin(existing_quarters)]
                    filtered_count = len(result)
                    
                    if original_count > filtered_count:
                        logger.info(f"📊 过滤掉 {original_count - filtered_count} 条已存在的季度数据，剩余 {filtered_count} 条新数据")
                    
                    if filtered_count == 0:
                        logger.info(f"ℹ️ 所有数据都已存在，跳过保存")
                        return True
                
                # 保存数据
                success = self._save_data(result)
                if success:
                    logger.info(f"✅ {self.config['table_name']} 更新完成")
                    return True
                else:
                    logger.error(f"❌ {self.config['table_name']} 数据保存失败")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ API调用失败 {api_config['method']}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ {self.config['table_name']} 更新失败: {e}")
            return False
