"""
股本信息更新器
"""

from typing import Dict, List, Any
from loguru import logger
from ...base_renewer import BaseRenewer


class ShareInfoRenewer(BaseRenewer):
    """股本信息更新器 - 多线程模式"""
    
    def build_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        """构建股本信息更新任务"""
        jobs = []
        
        try:
            # 获取股票列表
            stock_index = self.storage.load_stock_index()
            if not stock_index:
                logger.warning("❌ 没有股票数据，无法构建股本信息更新任务")
                return []
            
            # 获取API配置
            api_config = self.config.get('apis', [])[0]
            api_method = api_config['method']
            
            # 为每只股票创建任务
            for stock in stock_index:
                stock_id = stock['id']
                
                # 使用配置中的参数模板
                api_params = {}
                for param_key, param_template in api_config['params'].items():
                    api_params[param_key] = param_template.format(
                        ts_code=stock_id,
                        start_date=start_date,
                        end_date=end_date
                    )
                
                jobs.append({
                    'ts_code': stock_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'api_method': api_method,
                    'api_params': api_params
                })
            
            logger.info(f"📊 构建了 {len(jobs)} 个股本信息更新任务")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ 构建股本信息任务失败: {e}")
            return []
    
    def combine_apis_data(self, api_results: Dict[str, Any]) -> Any:
        """合并API数据（不应用字段映射，让BaseRenewer处理）"""
        if len(api_results) == 1:
            result = list(api_results.values())[0]
            
            if result is None or (hasattr(result, 'empty') and result.empty):
                logger.info("ℹ️ Share Info 没有新数据")
                return result
            
            logger.info(f"📊 Share Info 原始数据字段: {list(result.columns)}")
            logger.info(f"📊 Share Info 数据行数: {len(result)}")
            
            # 预处理：
            # - 将 trade_date 转换为 quarter（YYYYQ[1-4]），便于与表主键匹配
            # - 将 shares 从“万股”转换为“股”（×10000）
            try:
                if hasattr(result, 'assign'):
                    def _date_to_quarter(date_str: str) -> str:
                        if not isinstance(date_str, str) or len(date_str) < 6:
                            return date_str
                        year = date_str[:4]
                        month = int(date_str[4:6])
                        if month <= 3:
                            return f"{year}Q1"
                        elif month <= 6:
                            return f"{year}Q2"
                        elif month <= 9:
                            return f"{year}Q3"
                        else:
                            return f"{year}Q4"

                    result = result.copy()
                    # 支持 stk_premarket 的 trade_date
                    if 'trade_date' in result.columns:
                        result['quarter'] = result['trade_date'].astype(str).map(_date_to_quarter)
                    # 兼容旧的 end_date 字段
                    elif 'end_date' in result.columns:
                        result['quarter'] = result['end_date'].astype(str).map(_date_to_quarter)

                    # shares 单位转换（万股 -> 股）
                    for col in ['total_share', 'float_share']:
                        if col in result.columns:
                            try:
                                result[col] = (result[col].astype(float) * 10000).round().astype('int64')
                            except Exception:
                                # 保底转换失败则跳过该列
                                pass
            except Exception as e:
                logger.error(f"❌ 股本数据预处理失败: {e}")
                return result
            
            # 过滤掉数据库中已存在的数据（incremental 模式需要）
            if len(result) > 0:
                try:
                    # 获取数据库中已存在的记录
                    existing_query = '''
                    SELECT CONCAT(id, '-', quarter) as unique_key
                    FROM share_info 
                    '''
                    existing_records = self.db.execute_sync_query(existing_query)
                    existing_keys = {row['unique_key'] for row in existing_records}
                    logger.info(f"📊 数据库中已有 {len(existing_keys)} 条股本记录")
                    
                    # 创建API数据的唯一键并过滤（与 DB 主键 id+quarter 对齐）
                    # 这里先用 ts_code（稍后映射为 id）+ quarter 去重
                    if 'ts_code' in result.columns and 'quarter' in result.columns:
                        result['unique_key'] = result['ts_code'].astype(str) + '-' + result['quarter'].astype(str)
                        original_count = len(result)
                        
                        # 过滤掉已存在的数据
                        mask = ~result['unique_key'].isin(existing_keys)
                        result = result[mask]
                        result = result.drop('unique_key', axis=1)  # 删除临时列
                        filtered_count = len(result)
                        
                        if original_count > filtered_count:
                            logger.info(f"📊 过滤掉 {original_count - filtered_count} 条已存在的股本数据，剩余 {filtered_count} 条新数据")
                        
                        if filtered_count == 0:
                            logger.info(f"ℹ️ 所有股本数据都已存在，跳过保存")
                            return None
                    else:
                        logger.warning(f"❌ API 数据缺少必要字段: ts_code 或 quarter")
                        return None
                        
                except Exception as e:
                    logger.error(f"❌ 数据过滤失败: {e}")
                    # 如果过滤失败，返回原始数据让数据库处理重复键错误
                    return result
            
            return result
        
        return None
