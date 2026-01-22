"""
股票列表 Handler

使用 Tushare Provider 获取股票列表（包含所有交易所）
使用当前日期时间作为 last_update（股票列表的更新时间）
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
import pandas as pd

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper


class TushareStockListHandler(BaseHandler):
    """
    股票列表 Handler
    
    从 Tushare 获取股票列表（包含所有交易所的股票）。
    
    特性：
    - 使用当前日期时间作为 last_update 字段（股票列表的更新时间）
    - 使用 upsert 模式更新数据
    - 包含所有交易所的股票（不排除北交所）
    
    配置（在 config.json 中）：
    - renew_mode: "refresh"
    - date_format: "none"
    - apis: {...} (包含 provider_name, method, params 等)
    """
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：设置 last_update 到 context
        
        Args:
            context: 执行上下文
            apis: ApiJob 列表（已注入日期范围）
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表
        """
        # last_update 是更新股票列表的时间，应该使用当前日期时间
        # 格式：YYYY-MM-DD HH:MM:SS（数据库 datetime 格式）
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        context["last_update"] = current_datetime
        return apis
    
    def _normalize_data(self, context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据：覆盖基类方法，添加 last_update 字段
        
        从 Tushare 返回的 DataFrame 中提取股票列表，进行字段映射和过滤
        
        特性：
        - 使用当前日期时间作为 last_update（股票列表的更新时间，格式：YYYY-MM-DD HH:MM:SS）
        - 字段映射与数据库 schema 保持一致
        """
        # 先使用基类的默认标准化逻辑
        config = context.get("config")
        if hasattr(config, "get_apis"):
            apis_conf = config.get_apis()
        else:
            apis_conf = config.get("apis") if config else {}
        schema = context.get("schema")
        
        if not fetched_data or not isinstance(fetched_data, dict):
            return {"data": []}
        
        # 使用 Helper 提取并映射记录
        mapped_records: List[Dict[str, Any]] = DataSourceHandlerHelper.extract_mapped_records(
            apis_conf=apis_conf,
            fetched_data=fetched_data,
        )
        
        if not mapped_records:
            return {"data": []}
        
        # 获取 last_update（从 context 获取，如果未设置则使用当前时间）
        last_update = context.get("last_update")
        if not last_update:
            last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 字段映射和数据处理
        formatted = []
        for item in mapped_records:
            # 字段映射（从 Tushare 字段映射到 schema 字段）
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
        
        # 应用 schema 约束
        normalized_records = DataSourceHandlerHelper.apply_schema(formatted, schema)
        
        logger.info(f"✅ 股票列表处理完成，共 {len(normalized_records)} 只股票（last_update: {last_update}）")
        
        return DataSourceHandlerHelper.build_normalized_payload(normalized_records)
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后的钩子：保存数据到数据库
        
        Args:
            context: 执行上下文
            normalized_data: 标准化后的数据
            
        Returns:
            Dict[str, Any]: 返回标准化后的数据
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法保存股票列表数据")
            return normalized_data
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过股票列表数据保存")
            return normalized_data
        
        # 验证数据格式
        data_list = normalized_data.get("data") if isinstance(normalized_data, dict) else None
        if not data_list:
            logger.debug("股票列表数据为空，无需保存")
            return normalized_data
        
        try:
            count = data_manager.stock.list.save(data_list)
            logger.info(f"✅ 保存股票列表数据完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存股票列表数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        return normalized_data
