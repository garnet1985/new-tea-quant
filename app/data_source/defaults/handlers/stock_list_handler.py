"""
股票列表 Handler

使用 Tushare Provider 获取股票列表，排除北交所
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
import pandas as pd

from typing import List, Dict, Any
from app.data_source.data_source_handler import BaseDataSourceHandler


class TushareStockListHandler(BaseDataSourceHandler):
    """
    股票列表 Handler
    
    从 Tushare 获取股票列表，排除北交所（.BJ 结尾）
    """
    
    # 类属性（必须定义）
    data_source = "stock_list"
    renew_type = "upsert"  # 使用 upsert 模式，更新现有记录
    description = "获取股票列表（排除北交所）"
    dependencies = []  # 无依赖
    
    # 可选类属性
    requires_date_range = False  # 不需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None):
        super().__init__(schema, params or {})
        
        # 从配置中获取是否排除北交所（默认排除）
        self.exclude_bj = self.get_param("exclude_bj", True)
        
        # 从配置中获取 API 字段列表（默认使用所有必要字段）
        self.api_fields = self.get_param(
            "api_fields",
            "ts_code,symbol,name,area,industry,market,exchange,list_date"
        )
    
    async def fetch(self, context: Dict[str, Any] = None) -> List:
        """
        生成获取股票列表的 Task
        
        逻辑：
        1. 调用 Tushare stock_basic API 获取所有股票
        2. 在 normalize 中处理字段映射和北交所排除
        """
        context = context or {}
        
        logger.debug("开始获取股票列表")
        
        # 使用辅助方法创建简单的单 API 调用 Task
        task = self.create_simple_task(
            provider_name="tushare",
            method="get_stock_list",
            params={
                "fields": self.api_fields,
            }
        )
        
        return [task]
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare 返回的 DataFrame 中提取股票列表，进行字段映射和过滤
        """
        # 使用辅助方法获取简单 Task 的结果
        df = self.get_simple_result(raw_data)
        
        if df is None or df.empty:
            logger.warning("股票列表查询返回空数据")
            return {"data": []}
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        # 字段映射和数据处理
        formatted = []
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        for item in records:
            # 排除北交所（如果配置了）
            ts_code = item.get('ts_code', '')
            if self.exclude_bj and str(ts_code).endswith('.BJ'):
                continue
            
            # 字段映射
            mapped = {
                "id": ts_code,
                "name": item.get('name', ''),
                "industry": item.get('industry') or '未知行业',
                "type": item.get('market') or '未知类型',
                "exchange_center": item.get('exchange') or '未知交易所',
                "is_active": 1,  # 从 API 获取的都是活跃股票
                "last_update": current_date,
            }
            
            # 只保留有效的记录（必须有 id 和 name）
            if mapped.get('id') and mapped.get('name'):
                formatted.append(mapped)
        
        logger.info(f"✅ 股票列表处理完成，共 {len(formatted)} 只股票（已排除BJ: {self.exclude_bj}）")
        
        return {
            "data": formatted
        }
