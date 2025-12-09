"""
PPI 数据 Handler

从 Tushare 获取 PPI 价格指数数据（月度）
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

from app.data_source.data_source_handler import BaseDataSourceHandler
from utils.date.date_utils import DateUtils


class PPIHandler(BaseDataSourceHandler):
    """
    PPI 数据 Handler
    
    从 Tushare 获取 PPI 价格指数数据（月度）。
    
    特点：
    - 月度数据（YYYYMM 格式）
    - 增量更新（incremental）
    - 需要计算日期范围（基于数据库最新记录）
    """
    
    # 类属性（必须定义）
    data_source = "ppi"
    renew_type = "incremental"  # 增量更新
    description = "获取 PPI 价格指数数据（月度）"
    dependencies = []  # 无依赖
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None):
        super().__init__(schema, params or {})
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        查询数据库获取最新月份，计算需要更新的日期范围
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return
        
        # 从 data_manager 查询数据库获取最新月份
        if self.data_manager:
            try:
                # TODO: 查询数据库获取最新月份
                logger.debug("从数据库查询最新月份（待实现）")
            except Exception as e:
                logger.warning(f"查询数据库失败，使用默认日期范围: {e}")
        
        # 如果没有数据库或查询失败，使用默认范围（最近 3 年）
        if "start_date" not in context or "end_date" not in context:
            current_date = DateUtils.get_current_date_str()
            current_year = int(current_date[:4])
            current_month = int(current_date[4:6])
            
            # 计算开始月份（3年前）
            start_year = current_year - 3
            start_month = 1
            
            context["start_date"] = f"{start_year}{start_month:02d}"
            context["end_date"] = f"{current_year}{current_month:02d}"
            logger.debug(f"使用默认日期范围: {context['start_date']} 至 {context['end_date']}")
    
    async def fetch(self, context: Dict[str, Any] = None) -> List:
        """
        生成获取 PPI 数据的 Task
        
        逻辑：
        1. 从 context 获取日期范围（月份格式 YYYYMM）
        2. 调用 Tushare ppi API 获取月度数据
        """
        context = context or {}
        
        start_date = context.get("start_date")
        end_date = context.get("end_date")
        
        if not start_date or not end_date:
            raise ValueError("PPI Handler 需要 start_date 和 end_date 参数")
        
        logger.debug(f"获取 PPI 数据: {start_date} 至 {end_date}")
        
        # 使用辅助方法创建简单的单 API 调用 Task
        task = self.create_simple_task(
            provider_name="tushare",
            method="get_ppi",
            params={
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        
        return [task]
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare 返回的 DataFrame 中提取 PPI 数据，进行字段映射
        """
        # 使用辅助方法获取简单 Task 的结果
        df = self.get_simple_result(raw_data)
        
        if df is None or df.empty:
            logger.warning("PPI 数据查询返回空数据")
            return {"data": []}
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        # 字段映射和数据处理
        formatted = []
        
        for item in records:
            # 字段映射（根据 legacy config）
            # API 字段：month, ppi_accu, ppi_yoy, ppi_mom
            month = str(item.get('month', ''))
            if not month:
                continue
            
            mapped = {
                "date": month,
                "ppi": float(item.get('ppi_accu', 0)) if item.get('ppi_accu') is not None else 0.0,
                "ppi_yoy": float(item.get('ppi_yoy', 0)) if item.get('ppi_yoy') is not None else 0.0,
                "ppi_mom": float(item.get('ppi_mom', 0)) if item.get('ppi_mom') is not None else 0.0,
            }
            
            formatted.append(mapped)
        
        logger.info(f"✅ PPI 数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }

