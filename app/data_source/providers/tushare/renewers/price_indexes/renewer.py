"""
价格指数更新器
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from loguru import logger
from ...base_renewer import BaseRenewer


class PriceIndexesRenewer(BaseRenewer):
    """价格指数更新器 - 需要自定义逻辑"""
    
    def should_renew(self, start_date: str = None, latest_market_open_day: str = None) -> Optional[str]:
        """自定义 should_renew 逻辑"""
        table_name = self.config['table_name']
        
        # 检查最新记录是否有空值
        last_record = self._get_last_record(table_name)
        if not last_record:
            return "20080101"  # 默认开始日期
        
        # 检查关键字段是否为空或0（宏观经济数据的关键字段）
        # 检查是否有缺失数据的记录
        has_missing_data = False
        for field in ['CPI', 'PPI', 'PMI']:
            field_value = last_record.get(field)
            if not field_value or field_value == 0:
                has_missing_data = True
        
        if has_missing_data:
            # 如果最新记录有缺失数据，从更早的记录开始更新
            # 查找最近一个有完整数据的记录
            complete_record_query = '''
            SELECT date FROM price_indexes 
            WHERE CPI IS NOT NULL AND CPI != 0 
            AND PPI IS NOT NULL AND PPI != 0 
            AND PMI IS NOT NULL AND PMI != 0
            ORDER BY date DESC LIMIT 1
            '''
            
            try:
                complete_records = self.db.execute_sync_query(complete_record_query)
                if complete_records:
                    complete_date = complete_records[0]['date']
                    return complete_date
                else:
                    return "20080101"
            except Exception as e:
                return "20080101"
        
        # 检查是否需要增量更新
        latest_date = self._get_latest_date(table_name, 'date')
        if latest_market_open_day and latest_date < latest_market_open_day:
            return latest_date
        
        return None
    
    def renew(self, latest_market_open_day: str = None) -> bool:
        """更新宏观经济数据（简单模式）"""
        try:
            logger.info(f"🔄 开始更新 {self.config['table_name']}")
            
            # 检查是否需要更新
            should_renew_date = self.should_renew(latest_market_open_day, latest_market_open_day)
            if should_renew_date:
                logger.info(f"📅 需要从 {should_renew_date} 开始更新")
                start_date = should_renew_date
            else:
                logger.info(f"ℹ️ {self.config['table_name']} 数据已是最新，跳过更新")
                return True
            
            # 将日期转换为月份格式
            def date_to_month(date_input) -> str:
                if hasattr(date_input, 'strftime'):  # datetime对象
                    return date_input.strftime('%Y%m')
                elif isinstance(date_input, str):
                    if len(date_input) == 8:  # YYYYMMDD
                        return date_input[:6]  # YYYYMM
                    elif len(date_input) == 10:  # YYYY-MM-DD
                        # 转换为 YYYYMM 格式
                        return date_input[:4] + date_input[5:7]
                    else:
                        return date_input[:6]  # 默认取前6位
                else:
                    return str(date_input)[:6]  # 其他类型转换为字符串
            
            start_month = date_to_month(start_date)
            end_month = date_to_month(latest_market_open_day)
            
            # 检查日期范围是否有效
            if start_month > end_month:
                start_month = end_month
            
            # 调用所有API获取数据
            api_results = {}
            for api_config in self.config.get('apis', []):
                api_name = api_config['name']
                api_method = getattr(self.api, api_config['method'])
                
                try:
                    # 准备API参数
                    api_params = {
                        'start_m': start_month,
                        'end_m': end_month
                    }
                    
                    logger.info(f"📊 调用API: {api_config['method']}")
                    result = api_method(**api_params)
                    api_results[api_name] = result
                    
                except Exception as e:
                    logger.error(f"❌ API调用失败 {api_config['method']}: {e}")
                    api_results[api_name] = None
            
            # 合并所有API数据
            combined_data = self.combine_apis_data(api_results)
            
            # 保存数据
            if combined_data is not None and not (hasattr(combined_data, 'empty') and combined_data.empty):
                success = self._save_data(combined_data)
                if success:
                    logger.info(f"✅ {self.config['table_name']} 更新完成")
                    return True
                else:
                    logger.error(f"❌ {self.config['table_name']} 数据保存失败")
                    return False
            else:
                logger.info(f"ℹ️ {self.config['table_name']} 没有新数据")
                return True
                
        except Exception as e:
            logger.error(f"❌ {self.config['table_name']} 更新失败: {e}")
            return False
    
    def combine_apis_data(self, api_results: Dict[str, Any]) -> Any:
        """合并多个宏观经济API的数据"""
        combined_data = {}
        
        for api_name, result in api_results.items():
            if result is None or (hasattr(result, 'empty') and result.empty):
                continue
            
            # 获取该API的字段映射
            api_config = None
            for api in self.config.get('apis', []):
                if api['name'] == api_name:
                    api_config = api
                    break
            
            if not api_config or 'mapping' not in api_config:
                continue
            
            mapping = api_config['mapping']
            
            for _, row in result.iterrows():
                # 获取月份字段（不同API可能使用不同的字段名）
                month_field = None
                for api_field, db_field in mapping.items():
                    if db_field == 'date':
                        month_field = api_field
                        break
                
                if month_field is None or month_field not in row:
                    continue
                    
                month = row[month_field]
                
                if month not in combined_data:
                    # 生成 id 字段：使用月份生成 YYYY-MM 格式
                    try:
                        if isinstance(month, str):
                            # 处理不同格式的月份数据
                            if len(month) == 6:  # YYYYMM 格式
                                month_obj = datetime.strptime(month, '%Y%m')
                            elif len(month) == 7:  # YYYY-MM 格式
                                month_obj = datetime.strptime(month, '%Y-%m')
                            else:
                                month_obj = datetime.strptime(month[:7], '%Y-%m')
                        elif hasattr(month, 'strftime'):  # datetime对象
                            month_obj = month
                        else:
                            month_obj = datetime.strptime(str(month)[:7], '%Y-%m')
                        
                        id_field = month_obj.strftime('%Y-%m')
                        # 将月份转换为完整的日期格式 (YYYY-MM-01)
                        date_field = month_obj.strftime('%Y-%m-%d')
                    except Exception as e:
                        logger.warning(f"❌ 月份解析失败: {month}, 错误: {e}")
                        id_field = str(month)[:7] if len(str(month)) >= 7 else str(month)
                        date_field = str(month)[:7] + '-01' if len(str(month)) >= 7 else str(month)
                    
                    combined_data[month] = {
                        'id': id_field,
                        'date': date_field
                    }
                
                # 应用字段映射
                for api_field, db_field in mapping.items():
                    if db_field == 'date':  # 跳过日期字段
                        continue
                    
                    if api_field in row:
                        value = row[api_field]
                        # 处理 NaN 值
                        if pd.isna(value):
                            # 对于数值字段，将 NaN 转换为 0.0
                            if db_field in ['CPI', 'CPI_yoy', 'CPI_mom', 'PPI', 'PPI_yoy', 'PPI_mom', 
                                           'PMI', 'PMI_l_scale', 'PMI_m_scale', 'PMI_s_scale',
                                           'M0', 'M0_yoy', 'M0_mom', 'M1', 'M1_yoy', 'M1_mom', 
                                           'M2', 'M2_yoy', 'M2_mom']:
                                combined_data[month][db_field] = 0.0
                            else:
                                combined_data[month][db_field] = None
                        else:
                            combined_data[month][db_field] = value
                    else:
                        # 如果字段不存在，设置默认值（对于必填字段）
                        if db_field in ['CPI', 'CPI_yoy', 'CPI_mom', 'PPI', 'PPI_yoy', 'PPI_mom', 
                                       'PMI', 'PMI_l_scale', 'PMI_m_scale', 'PMI_s_scale',
                                       'M0', 'M0_yoy', 'M0_mom', 'M1', 'M1_yoy', 'M1_mom', 
                                       'M2', 'M2_yoy', 'M2_mom']:
                            combined_data[month][db_field] = 0.0  # 设置默认值为 0.0
        
        result_df = pd.DataFrame(list(combined_data.values()))
        return result_df
    
    def _get_last_record(self, table_name: str) -> Optional[Dict]:
        """获取最新记录"""
        try:
            query = f"SELECT * FROM {table_name} ORDER BY date DESC LIMIT 1"
            result = self.db.execute_sync_query(query)
            return result[0] if result else None
        except Exception as e:
            logger.warning(f"❌ 获取最新记录失败: {e}")
            return None
