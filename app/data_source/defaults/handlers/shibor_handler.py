"""
Shibor 数据 Handler

从 Tushare 获取 Shibor 利率数据（日度）
"""
from typing import List, Dict, Any
from loguru import logger

from app.data_source.data_source_handler import BaseDataSourceHandler


class ShiborHandler(BaseDataSourceHandler):
    """
    Shibor 数据 Handler
    
    从 Tushare 获取 Shibor 利率数据（日度）。
    
    特点：
    - 日度数据（每个工作日发布）
    - 增量更新（incremental）
    - 需要计算日期范围（基于数据库最新记录）
    """
    
    # 类属性（必须定义）
    data_source = "shibor"
    renew_type = "incremental"  # 增量更新
    description = "获取 Shibor 利率数据（日度）"
    dependencies = []  # 无依赖
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None):
        super().__init__(schema, params or {})
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        查询数据库获取最新日期，计算需要更新的日期范围
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return
        
        # 从 data_manager 查询数据库获取最新日期
        if self.data_manager:
            try:
                # TODO: 查询数据库获取最新日期
                logger.debug("从数据库查询最新日期（待实现）")
            except Exception as e:
                logger.warning(f"查询数据库失败，使用默认日期范围: {e}")
        
        # 如果没有数据库或查询失败，使用默认范围（最近 1 年）
        if "start_date" not in context or "end_date" not in context:
            from datetime import datetime, timedelta
            from utils.date.date_utils import DateUtils
            
            end_date = DateUtils.get_current_date_str()
            start_date = DateUtils.get_date_before_days(end_date, 365)  # 最近 1 年
            
            context["start_date"] = start_date
            context["end_date"] = end_date
            logger.debug(f"使用默认日期范围: {context['start_date']} 至 {context['end_date']}")
    
    async def fetch(self, context: Dict[str, Any] = None) -> List:
        """
        生成获取 Shibor 数据的 Task
        
        逻辑：
        1. 从 context 获取日期范围
        2. 调用 Tushare shibor API 获取日度数据
        """
        context = context or {}
        
        start_date = context.get("start_date")
        end_date = context.get("end_date")
        
        if not start_date or not end_date:
            raise ValueError("Shibor Handler 需要 start_date 和 end_date 参数")
        
        logger.debug(f"获取 Shibor 数据: {start_date} 至 {end_date}")
        
        # 使用辅助方法创建简单的单 API 调用 Task
        task = self.create_simple_task(
            provider_name="tushare",
            method="get_shibor",
            params={
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        
        return [task]
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare 返回的 DataFrame 中提取 Shibor 数据，进行字段映射
        """
        # 使用辅助方法获取简单 Task 的结果
        df = self.get_simple_result(raw_data)
        
        if df is None or df.empty:
            logger.warning("Shibor 数据查询返回空数据")
            return {"data": []}
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        # 字段映射和数据处理
        formatted = []
        
        for item in records:
            # 字段映射（根据 legacy config）
            # API 字段：date, on, 1w, 1m, 3m, 1y
            mapped = {
                "date": str(item.get('date', '')),
                "one_night": float(item.get('on', 0)) if item.get('on') is not None else 0.0,
                "one_week": float(item.get('1w', 0)) if item.get('1w') is not None else 0.0,
                "one_month": float(item.get('1m', 0)) if item.get('1m') is not None else 0.0,
                "three_month": float(item.get('3m', 0)) if item.get('3m') is not None else 0.0,
                "one_year": float(item.get('1y', 0)) if item.get('1y') is not None else 0.0,
            }
            
            # 只保留有效的记录（必须有 date）
            if mapped.get('date'):
                formatted.append(mapped)
        
        logger.info(f"✅ Shibor 数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }

