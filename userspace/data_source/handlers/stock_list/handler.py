"""
股票列表 Handler

使用 Tushare Provider 获取股票列表（包含所有交易所）
使用当前日期时间作为 last_update（股票列表的更新时间）
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

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
    
    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        字段映射后的钩子：添加 last_update 字段并过滤无效记录
        
        Args:
            context: 执行上下文
            mapped_records: 已应用 field_mapping 的记录列表
            
        Returns:
            List[Dict[str, Any]]: 处理后的记录列表
        """
        # 获取 last_update（从 context 获取，如果未设置则使用当前时间）
        last_update = context.get("last_update")
        if not last_update:
            last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 添加字段并过滤
        formatted = []
        for item in mapped_records:
            # 添加 last_update 和 is_active 字段
            item["last_update"] = last_update
            item["is_active"] = 1  # 从 API 获取的都是活跃股票
            
            # 处理默认值
            if not item.get("industry"):
                item["industry"] = "未知行业"
            if not item.get("type"):
                item["type"] = "未知类型"
            if not item.get("exchange_center"):
                item["exchange_center"] = "未知交易所"
            
            # 只保留有效的记录（必须有 id 和 name）
            if item.get('id') and item.get('name'):
                formatted.append(item)
        
        logger.info(f"✅ 股票列表处理完成，共 {len(formatted)} 只股票（last_update: {last_update}）")
        
        return formatted
    
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
