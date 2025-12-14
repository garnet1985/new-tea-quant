"""
股票列表 Handler

使用 Tushare Provider 获取股票列表（包含所有交易所）
参考 legacy 逻辑：使用最新交易日作为 last_update
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
import pandas as pd

from typing import List, Dict, Any
from app.data_source.data_source_handler import BaseDataSourceHandler
from utils.date.date_utils import DateUtils


class TushareStockListHandler(BaseDataSourceHandler):
    """
    股票列表 Handler
    
    从 Tushare 获取股票列表（包含所有交易所的股票）。
    
    参考 legacy 逻辑：
    - 使用最新交易日作为 last_update 字段
    - 使用 upsert 模式更新数据
    
    配置参数：
    - api_fields (str): API 字段列表，默认包含所有必要字段
    """
    
    # 类属性（必须定义）
    data_source = "stock_list"
    renew_type = "upsert"  # 使用 upsert 模式，更新现有记录
    description = "获取股票列表"
    dependencies = []  # 无依赖
    
    # 可选类属性
    requires_date_range = False  # 不需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)
        
        # 从配置中获取 API 字段列表（默认使用所有必要字段）
        self.api_fields = self.get_param(
            "api_fields",
            "ts_code,symbol,name,area,industry,market,exchange,list_date"
        )
        
        # 存储最新交易日（在 before_fetch 中设置）
        self._latest_trading_date = None
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        获取最新交易日，用于设置 last_update 字段
        """
        context = context or {}
        
        # 如果 context 中已有最新交易日，直接使用
        if "latest_trading_date" in context:
            self._latest_trading_date = context["latest_trading_date"]
            return
        
        # 从 data_manager 获取最新交易日
        if self.data_manager:
            try:
                latest_trading_date = self.data_manager.get_latest_trading_date()
                # TradingDateCache 返回的是 YYYYMMDD 格式，直接使用（MySQL datetime 字段支持此格式）
                self._latest_trading_date = latest_trading_date
                context["latest_trading_date"] = latest_trading_date
                logger.debug(f"获取最新交易日: {latest_trading_date}")
            except Exception as e:
                logger.warning(f"获取最新交易日失败，使用昨天作为 fallback: {e}")
                # 如果获取失败，使用昨天（因为今天可能交易还没有完成）
                yesterday = DateUtils.get_date_before_days(DateUtils.get_current_date_str(), 1)
                self._latest_trading_date = yesterday
                context["latest_trading_date"] = yesterday
        else:
            # 如果没有 data_manager，使用昨天（因为今天可能交易还没有完成）
            yesterday = DateUtils.get_date_before_days(DateUtils.get_current_date_str(), 1)
            self._latest_trading_date = yesterday
            context["latest_trading_date"] = yesterday
    
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
        
        参考 legacy 逻辑：
        - 使用最新交易日作为 last_update
        - 字段映射与 legacy 保持一致
        """
        # 使用辅助方法获取简单 Task 的结果
        df = self.get_simple_result(task_results)
        
        if df is None or df.empty:
            logger.warning("股票列表查询返回空数据")
            return {"data": []}
        
        # 获取最新交易日（从实例变量获取，如果未设置则使用昨天）
        if not self._latest_trading_date:
            if self.data_manager:
                try:
                    self._latest_trading_date = self.data_manager.get_latest_trading_date()
                except Exception as e:
                    logger.warning(f"获取最新交易日失败，使用昨天作为 fallback: {e}")
                    # 使用昨天（因为今天可能交易还没有完成）
                    self._latest_trading_date = DateUtils.get_date_before_days(DateUtils.get_current_date_str(), 1)
            else:
                # 使用昨天（因为今天可能交易还没有完成）
                self._latest_trading_date = DateUtils.get_date_before_days(DateUtils.get_current_date_str(), 1)
        
        latest_trading_date = self._latest_trading_date
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        # 字段映射和数据处理（参考 legacy config.py）
        formatted = []
        
        for item in records:
            # 字段映射（与 legacy 保持一致）
            ts_code = item.get('ts_code', '')
            mapped = {
                "id": ts_code,
                "name": item.get('name', ''),
                "industry": item.get('industry') or '未知行业',
                "type": item.get('market') or '未知类型',
                "exchange_center": item.get('exchange') or '未知交易所',
                "is_active": 1,  # 从 API 获取的都是活跃股票
                "last_update": latest_trading_date,  # 使用最新交易日
            }
            
            # 只保留有效的记录（必须有 id 和 name）
            if mapped.get('id') and mapped.get('name'):
                formatted.append(mapped)
        
        logger.info(f"✅ 股票列表处理完成，共 {len(formatted)} 只股票（last_update: {latest_trading_date}）")
        
        return {
            "data": formatted
        }
