"""
GDP 数据 Handler

从 Tushare 获取 GDP 季度数据
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

from app.data_source.data_source_handler import BaseDataSourceHandler


class GDPHandler(BaseDataSourceHandler):
    """
    GDP 数据 Handler
    
    从 Tushare 获取 GDP 季度数据。
    
    特点：
    - 季度数据（YYYYQ[1-4] 格式）
    - 增量更新（incremental）
    - 需要计算日期范围（基于数据库最新记录）
    """
    
    # 类属性（必须定义）
    data_source = "gdp"
    renew_type = "incremental"  # 增量更新
    description = "获取 GDP 季度数据"
    dependencies = []  # 无依赖
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None):
        super().__init__(schema, params or {})
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        查询数据库获取最新季度，计算需要更新的日期范围
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return
        
        # 从 data_manager 查询数据库获取最新季度
        if self.data_manager:
            try:
                # TODO: 查询数据库获取最新季度
                # 这里需要实现查询逻辑
                # latest_quarter = await self._get_latest_quarter_from_db()
                # context["start_date"] = self._calculate_start_quarter(latest_quarter)
                # context["end_date"] = self._calculate_end_quarter()
                logger.debug("从数据库查询最新季度（待实现）")
            except Exception as e:
                logger.warning(f"查询数据库失败，使用默认日期范围: {e}")
        
        # 如果没有数据库或查询失败，使用默认范围（最近 5 年）
        if "start_date" not in context or "end_date" not in context:
            # 默认：最近 5 年的数据
            current_year = datetime.now().year
            context["start_date"] = f"{current_year - 5}Q1"
            context["end_date"] = f"{current_year}Q4"
            logger.debug(f"使用默认日期范围: {context['start_date']} 至 {context['end_date']}")
    
    async def fetch(self, context: Dict[str, Any] = None) -> List:
        """
        生成获取 GDP 数据的 Task
        
        逻辑：
        1. 从 context 获取日期范围
        2. 调用 Tushare cn_gdp API 获取季度数据
        """
        context = context or {}
        
        start_date = context.get("start_date")
        end_date = context.get("end_date")
        
        if not start_date or not end_date:
            raise ValueError("GDP Handler 需要 start_date 和 end_date 参数")
        
        logger.debug(f"获取 GDP 数据: {start_date} 至 {end_date}")
        
        # 使用辅助方法创建简单的单 API 调用 Task
        task = self.create_simple_task(
            provider_name="tushare",
            method="get_gdp",
            params={
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        
        return [task]
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare 返回的 DataFrame 中提取 GDP 数据，进行字段映射
        """
        # 使用辅助方法获取简单 Task 的结果
        df = self.get_simple_result(raw_data)
        
        if df is None or df.empty:
            logger.warning("GDP 数据查询返回空数据")
            return {"data": []}
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        # 字段映射和数据处理
        formatted = []
        
        for item in records:
            # 字段映射（根据 legacy config）
            # Tushare API 返回的字段名：quarter, gdp, gdp_yoy, pi, pi_yoy, si, si_yoy, ti, ti_yoy
            mapped = {
                "quarter": item.get('quarter', ''),
                "gdp": float(item.get('gdp', 0)) if item.get('gdp') is not None else 0.0,
                "gdp_yoy": float(item.get('gdp_yoy', 0)) if item.get('gdp_yoy') is not None else 0.0,
                "primary_industry": float(item.get('pi', 0)) if item.get('pi') is not None else 0.0,
                "primary_industry_yoy": float(item.get('pi_yoy', 0)) if item.get('pi_yoy') is not None else 0.0,
                "secondary_industry": float(item.get('si', 0)) if item.get('si') is not None else 0.0,
                "secondary_industry_yoy": float(item.get('si_yoy', 0)) if item.get('si_yoy') is not None else 0.0,
                "tertiary_industry": float(item.get('ti', 0)) if item.get('ti') is not None else 0.0,
                "tertiary_industry_yoy": float(item.get('ti_yoy', 0)) if item.get('ti_yoy') is not None else 0.0,
            }
            
            # 只保留有效的记录（必须有 quarter）
            if mapped.get('quarter'):
                formatted.append(mapped)
        
        logger.info(f"✅ GDP 数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }

