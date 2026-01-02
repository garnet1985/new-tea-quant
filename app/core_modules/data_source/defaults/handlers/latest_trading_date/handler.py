"""
最新交易日 Handler

使用 Tushare Provider 获取最新交易日
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger

from typing import List, Dict, Any
from app.data_source.data_source_handler import BaseDataSourceHandler


class LatestTradingDateHandler(BaseDataSourceHandler):
    """
    最新交易日 Handler
    
    从 Tushare 获取最新交易日
    """
    
    # 类属性（必须定义）
    data_source = "latest_trading_date"
    description = "获取最新交易日"
    dependencies = []  # 无依赖
    
    # 可选类属性
    requires_date_range = False  # 不需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)
        
        # 从配置中获取向后检查天数（默认15天）
        self.backward_checking_days = self.get_param("backward_checking_days", 15)
    
    async def fetch(self, context: Dict[str, Any] = None) -> List:
        """
        生成获取最新交易日的 Task
        
        逻辑：
        1. 从昨天往前推 N 天查询交易日历
        2. 找到 is_open == 1 的最大日期
        """
        context = context or {}
        
        # 计算查询日期范围
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        end_date = yesterday.strftime('%Y%m%d')
        start_date = (yesterday - timedelta(days=self.backward_checking_days)).strftime('%Y%m%d')
        
        # 使用辅助方法创建简单的单 API 调用 Task
        task = self.create_simple_task(
            provider_name="tushare",
            method="get_trade_cal",
            params={
                "exchange": "",  # 空字符串表示所有交易所
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        
        return [task]
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare 返回的 DataFrame 中提取最新交易日
        
        返回格式：{"data": [{"date": "YYYYMMDD"}]}
        """
        # 使用辅助方法获取简单 Task 的结果
        df = self.get_simple_result(raw_data)
        
        if df is None or df.empty:
            # 如果查询失败，使用昨天作为默认值
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning(f"交易日历查询失败，使用昨天作为默认值: {yesterday}")
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

