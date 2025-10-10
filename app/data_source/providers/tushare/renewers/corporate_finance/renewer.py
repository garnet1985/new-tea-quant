"""
企业财务指标更新器

使用Tushare的fina_indicator接口获取企业财务指标数据
"""

from typing import Dict, List, Any, Optional
from loguru import logger
import pandas as pd
from app.data_source.data_source_service import DataSourceService
from ...base_renewer import BaseRenewer


class CorporateFinanceRenewer(BaseRenewer):
    """企业财务指标更新器"""
    
    def build_jobs(self, latest_market_open_day: str, stock_list: list = None, 
                   db_records: Optional[List[Dict]] = None) -> List[Dict]:
        """
        构建财务数据更新任务
        
        思路：
        1. 为每只股票检查最新的财务数据季度
        2. 如果有gap，生成从gap到当前季度的所有period任务
        3. period格式为YYYYMMDD（季度末日期，如20231231）
        
        Args:
            latest_market_open_day: 最新交易日（YYYYMMDD）
            stock_list: 股票列表
            db_records: 数据库中的现有记录（用于增量更新）
            
        Returns:
            List[Dict]: 任务列表
        """
        if not stock_list:
            logger.warning("❌ 股票列表为空，无法构建财务数据更新任务")
            return []
        
        jobs = []
        
        # 计算当前季度（基于latest_market_open_day）
        current_quarter = DataSourceService.date_to_quarter(latest_market_open_day)
        
        # 构建db_records_map（按股票ID分组）
        db_records_map = {}
        if db_records:
            for record in db_records:
                stock_id = record.get('id')
                quarter = record.get('quarter')
                if stock_id and quarter:
                    if stock_id not in db_records_map:
                        db_records_map[stock_id] = []
                    db_records_map[stock_id].append(quarter)
        
        # 为每只股票构建任务
        for stock in stock_list:
            stock_id = stock.get('id')
            stock_name = stock.get('name', stock_id)
            market = stock.get('exchangeCenter', '')
            
            if not stock_id:
                continue
            
            # 获取该股票最新的财务数据季度
            latest_quarter = None
            if stock_id in db_records_map and db_records_map[stock_id]:
                # 找到最新的季度
                latest_quarter = max(db_records_map[stock_id])
            
            # 确定需要更新的季度范围
            if latest_quarter:
                # 计算时间差（按季度）
                time_gap = DataSourceService.time_gap_by('quarter', latest_quarter, current_quarter)
                
                if time_gap <= 0:
                    # 数据已是最新
                    continue
                
                # 从下一个季度开始更新
                start_quarter = DataSourceService.to_next('quarter', latest_quarter)
            else:
                # 没有数据，从配置的默认开始日期开始（如2018Q1）
                start_quarter = '2018Q1'  # 可配置
            
            # 生成所有需要更新的季度
            periods = self._generate_quarters(start_quarter, current_quarter)
            
            # 为每个季度创建任务
            for period in periods:
                # 将季度转换为period参数（YYYYMMDD格式）
                period_date = DataSourceService.quarter_to_date(period)
                
                jobs.append({
                    'ts_code': stock_id,
                    'period': period_date,  # API参数
                    '_quarter': period,  # 用于保存到数据库
                    '_log_vars': {
                        'id': stock_id,  # 用于日志模板
                        'stock_name': stock_name,
                        'market': market
                    }
                })
        
        logger.info(f"📊 构建了 {len(jobs)} 个财务数据更新任务")
        return jobs
    
    def prepare_data_for_save(self, data: Any, job: Dict) -> Any:
        """
        准备数据用于保存
        
        处理：
        1. 将_end_date转换为quarter字段
        2. 添加quarter到每条记录
        
        Args:
            data: API返回的数据（DataFrame或Dict）
            job: 当前任务信息
            
        Returns:
            处理后的数据
        """
        if not data:
            return data
        
        # 从job中获取quarter
        quarter = job.get('_quarter')
        if not quarter:
            logger.warning(f"⚠️  任务缺少_quarter字段: {job}")
            return None
        
        # 如果是DataFrame
        if isinstance(data, pd.DataFrame):
            if data.empty:
                return data
            
            # 添加quarter列
            data['quarter'] = quarter
            
            # 删除不需要的字段
            if '_end_date' in data.columns:
                data = data.drop(columns=['_end_date'])
            
            return data
        
        # 如果是dict
        elif isinstance(data, dict):
            for api_name, api_data in data.items():
                if isinstance(api_data, pd.DataFrame) and not api_data.empty:
                    api_data['quarter'] = quarter
                    if '_end_date' in api_data.columns:
                        api_data = api_data.drop(columns=['_end_date'])
                    data[api_name] = api_data
            
            return data
        
        return data
    
    def _generate_quarters(self, start_quarter: str, end_quarter: str) -> List[str]:
        """
        生成从start_quarter到end_quarter的所有季度列表
        
        Args:
            start_quarter: 开始季度（如'2018Q1'）
            end_quarter: 结束季度（如'2023Q4'）
            
        Returns:
            List[str]: 季度列表
        """
        quarters = []
        current = start_quarter
        
        # 解析季度
        start_year = int(start_quarter[:4])
        start_q = int(start_quarter[-1])
        end_year = int(end_quarter[:4])
        end_q = int(end_quarter[-1])
        
        # 生成所有季度
        year = start_year
        q = start_q
        
        while year < end_year or (year == end_year and q <= end_q):
            quarters.append(f"{year}Q{q}")
            
            # 递增季度
            q += 1
            if q > 4:
                q = 1
                year += 1
        
        return quarters
