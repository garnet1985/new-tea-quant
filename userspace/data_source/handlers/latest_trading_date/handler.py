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
    
    def _normalize_data(self, context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据：覆盖基类方法，提取最新交易日
        
        从 Tushare 返回的 DataFrame 中提取最新交易日
        
        返回格式：{"data": [{"date": "YYYYMMDD"}]}
        """
        if not fetched_data or not isinstance(fetched_data, dict):
            # 如果查询失败，使用昨天作为默认值
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning(f"交易日历查询失败，使用昨天作为默认值: {yesterday}")
            return {"data": [{"date": yesterday}]}
        
        # 获取第一个 API 的结果（通常只有一个 API）
        api_results = list(fetched_data.values())
        if not api_results:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning("交易日历查询返回空数据，使用昨天作为默认值")
            return {"data": [{"date": yesterday}]}
        
        # 获取第一个 job 的结果
        first_result = api_results[0]
        if not first_result:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning("交易日历查询返回空结果，使用昨天作为默认值")
            return {"data": [{"date": yesterday}]}
        
        # 转换为 DataFrame（如果还不是）
        import pandas as pd
        if not isinstance(first_result, pd.DataFrame):
            df = pd.DataFrame(first_result) if isinstance(first_result, list) else pd.DataFrame([first_result])
        else:
            df = first_result
        
        if df.empty:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning("交易日历数据为空，使用昨天作为默认值")
            return {"data": [{"date": yesterday}]}
        
        # 检查字段名
        if 'is_open' not in df.columns:
            logger.warning("交易日历数据缺少 is_open 字段，使用昨天作为默认值")
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            return {"data": [{"date": yesterday}]}
        
        # 筛选交易日（is_open == 1）
        trading_days = df[df['is_open'] == 1]
        
        if trading_days.empty:
            logger.warning("未找到交易日，使用昨天作为默认值")
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            return {"data": [{"date": yesterday}]}
        
        # 获取最大日期（最新交易日）
        latest_date = trading_days['cal_date'].max()
        
        logger.info(f"✅ 获取最新交易日: {latest_date}")
        
        # 返回符合 schema 验证的格式：{"data": [{"date": "YYYYMMDD"}]}
        return {
            "data": [{"date": str(latest_date)}]
        }
