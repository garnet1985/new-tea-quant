"""
价格指数更新器

使用 Tushare 的 cn_cpi, cn_ppi, cn_pmi, cn_m 接口获取宏观经济数据
"""

from typing import Dict, Any
import pandas as pd
from loguru import logger
from ...base_renewer import BaseRenewer


class PriceIndexesRenewer(BaseRenewer):
    """
    价格指数更新器
    
    特点：
    - 宏观数据，使用 simple 模式（一个任务）
    - 需要合并 4 个 API 的数据（CPI、PPI、PMI、货币供应）
    - 使用月份作为时间单位
    - prepare_data_for_save: 需要复写（合并多个API）
    """
    
    def prepare_data_for_save(self, api_results: Dict[str, Any], job: Dict = None) -> Any:
        """
        合并 4 个宏观经济 API 的数据
        
        策略：
        1. 每个API都已经通过 map_api_data 映射到 DB 字段
        2. 按 'date' 字段（月份）进行外连接合并
        3. 允许部分字段缺失（某些月份可能只有部分指标）
        
        Args:
            api_results: {api_name: mapped_data}，每个已映射为DB字段
            job: 任务信息（宏观数据通常只有一个任务）
            
        Returns:
            pd.DataFrame: 合并后的数据
        """
        if not api_results:
            return None
        
        # 将所有API数据转为DataFrame
        dfs = []
        for api_name, data in api_results.items():
            if data is None:
                logger.warning(f"⚠️  API {api_name} 返回空数据")
                continue
            
            df = pd.DataFrame(data) if not isinstance(data, pd.DataFrame) else data
            
            if df.empty:
                logger.warning(f"⚠️  API {api_name} 数据为空")
                continue
            
            # 调试：检查字段
            if 'date' not in df.columns:
                logger.error(f"❌ API {api_name} 数据中缺少 'date' 字段！字段列表: {df.columns.tolist()}")
                continue
            
            logger.debug(f"✅ API {api_name}: {len(df)} 条记录, 字段: {df.columns.tolist()}")
            dfs.append(df)
        
        if not dfs:
            logger.warning("⚠️  所有 API 都返回空数据或缺少必要字段")
            return None
        
        # 按 'date' 字段合并（外连接，保留所有月份）
        merged = dfs[0]
        for i, df in enumerate(dfs[1:], 2):
            logger.debug(f"合并第 {i} 个 DataFrame...")
            merged = pd.merge(merged, df, on='date', how='outer')
        
        # 按日期排序
        merged = merged.sort_values('date')
        
        logger.info(f"📊 合并完成：{len(merged)} 条记录, 字段: {merged.columns.tolist()}")
        
        return merged
