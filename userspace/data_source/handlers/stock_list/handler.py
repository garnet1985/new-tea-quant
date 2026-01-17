"""
股票列表 Handler

使用 Tushare Provider 获取股票列表（包含所有交易所）
使用当前日期时间作为 last_update（股票列表的更新时间）
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
import pandas as pd

from typing import List, Dict, Any
from core.modules.data_source.data_source_handler import BaseDataSourceHandler
from core.utils.date.date_utils import DateUtils


class TushareStockListHandler(BaseDataSourceHandler):
    """
    股票列表 Handler
    
    从 Tushare 获取股票列表（包含所有交易所的股票）。
    
    特性：
    - 使用当前日期时间作为 last_update 字段（股票列表的更新时间）
    - 使用 upsert 模式更新数据
    - 包含所有交易所的股票（不排除北交所）
    
    配置参数：
    - api_fields (str): API 字段列表，默认包含所有必要字段
    """
    
    # 类属性（必须定义）
    data_source = "stock_list"
    description = "获取股票列表"
    dependencies = []  # 无依赖
    
    # 可选类属性
    requires_date_range = False  # 不需要日期范围参数
    
    def __init__(self, schema, data_manager=None, definition=None):
        super().__init__(schema, data_manager, definition)
        
        # 从配置中获取 API 字段列表（默认使用所有必要字段）
        self.api_fields = self.get_param(
            "api_fields",
            "ts_code,symbol,name,area,industry,market,exchange,list_date"
        )
        
        # 存储 last_update（在 before_fetch 中设置）
        self._last_update = None
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        准备当前日期时间，用于设置 last_update 字段（股票列表的更新时间）
        """
        context = context or {}
        
        # last_update 是更新股票列表的时间，应该使用当前日期时间
        # 格式：YYYY-MM-DD HH:MM:SS（数据库 datetime 格式）
        from datetime import datetime
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._last_update = current_datetime
        context["last_update"] = current_datetime
        logger.debug(f"设置 last_update: {current_datetime}")
    
    async def fetch(self, context: Dict[str, Any] = None) -> List:
        """
        生成获取股票列表的 Task
        
        逻辑：
        1. 调用 Tushare stock_basic API 获取所有股票
        2. 在 normalize 中处理字段映射
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
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare 返回的 DataFrame 中提取股票列表，进行字段映射和过滤
        
        特性：
        - 使用当前日期时间作为 last_update（股票列表的更新时间，格式：YYYY-MM-DD HH:MM:SS）
        - 字段映射与数据库 schema 保持一致
        """
        # 使用辅助方法获取简单 Task 的结果
        df = self.get_simple_result(task_results)
        
        if df is None or df.empty:
            logger.warning("股票列表查询返回空数据")
            return {"data": []}
        
        # 获取 last_update（从实例变量获取，如果未设置则使用当前时间）
        if not self._last_update:
            from datetime import datetime
            self._last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        last_update = self._last_update
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        # 字段映射和数据处理
        formatted = []
        
        for item in records:
            # 字段映射
            ts_code = item.get('ts_code', '')
            
            mapped = {
                "id": ts_code,
                "name": item.get('name', ''),
                "industry": item.get('industry') or '未知行业',
                "type": item.get('market') or '未知类型',
                "exchange_center": item.get('exchange') or '未知交易所',
                "is_active": 1,  # 从 API 获取的都是活跃股票
                "last_update": last_update,  # 使用当前日期时间（更新股票列表的时间）
            }
            
            # 只保留有效的记录（必须有 id 和 name）
            if mapped.get('id') and mapped.get('name'):
                formatted.append(mapped)
        
        logger.info(f"✅ 股票列表处理完成，共 {len(formatted)} 只股票（last_update: {last_update}）")
        
        return {
            "data": formatted
        }
    
    async def after_normalize(self, normalized_data: Dict[str, Any]):
        """
        标准化后的钩子：保存数据到数据库
        
        在数据标准化完成后，自动保存到数据库。
        """
        data_list = self._validate_data_for_save(normalized_data)
        if not data_list:
            return
        
        try:
            count = self.data_manager.stock.list.save(data_list)
            logger.info(f"✅ 保存 {self.data_source} 数据完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存 {self.data_source} 数据失败: {e}")
            raise
