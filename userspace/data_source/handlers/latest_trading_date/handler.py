"""
最新交易日 Handler

使用 Tushare Provider 获取最新交易日
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper


class LatestTradingDateHandler(BaseHandler):
    """
    最新交易日 Handler
    
    从 Tushare 获取最新交易日
    
    配置（在 config.json 中）：
    - renew_mode: "refresh"
    - date_format: "none"
    - backward_checking_days: 15 (向后检查天数)
    - apis: {...} (包含 provider_name, method, params 等)
    """
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：动态设置查询日期范围
        
        Args:
            context: 执行上下文
            apis: ApiJob 列表
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表（已注入日期范围）
        """
        config = context.get("config")
        # 从配置中获取向后检查天数（默认15天）
        if hasattr(config, "get"):
            backward_checking_days = config.get("backward_checking_days", 15)
        else:
            backward_checking_days = getattr(config, "backward_checking_days", 15) if hasattr(config, "backward_checking_days") else 15
        
        # 计算查询日期范围
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        end_date = yesterday.strftime('%Y%m%d')
        start_date = (yesterday - timedelta(days=backward_checking_days)).strftime('%Y%m%d')
        
        # 为每个 ApiJob 注入日期范围参数
        for api_job in apis:
            if api_job.params is None:
                api_job.params = {}
            api_job.params["start_date"] = start_date
            api_job.params["end_date"] = end_date
            api_job.params["exchange"] = ""  # 空字符串表示所有交易所
        
        return apis
    
    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        字段映射后的钩子：筛选交易日并提取最新日期
        
        Args:
            context: 执行上下文
            mapped_records: 已应用 field_mapping 的记录列表
            
        Returns:
            List[Dict[str, Any]]: 只包含最新交易日的单条记录列表
        """
        if not mapped_records:
            # 如果查询失败，使用昨天作为默认值
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning(f"交易日历查询失败，使用昨天作为默认值: {yesterday}")
            return [{"date": yesterday}]
        
        # 筛选交易日（is_open == 1）
        trading_days = [r for r in mapped_records if r.get('is_open') == 1]
        
        if not trading_days:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning("未找到交易日，使用昨天作为默认值")
            return [{"date": yesterday}]
        
        # 找到最大日期（最新交易日）
        latest_date = None
        for record in trading_days:
            # 尝试从 cal_date 或 date 字段获取日期
            date_value = record.get('cal_date') or record.get('date')
            if date_value:
                # 使用 DateUtils 统一日期格式
                from core.utils.date.date_utils import DateUtils, DateFormat
                try:
                    date_str = DateUtils.normalize_to_format(date_value, DateFormat.DAY)
                    if date_str and (not latest_date or date_str > latest_date):
                        latest_date = date_str
                except Exception:
                    # 如果 DateUtils 无法解析，fallback 到原来的逻辑
                    date_str = str(date_value).replace('-', '')
                    if not latest_date or date_str > latest_date:
                        latest_date = date_str
        
        if not latest_date:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning("无法提取交易日，使用昨天作为默认值")
            return [{"date": yesterday}]
        
        logger.info(f"✅ 获取最新交易日: {latest_date}")
        
        # 返回单条记录
        return [{"date": latest_date}]
