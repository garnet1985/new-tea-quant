"""
简单 API Handler - 配置驱动的通用 Handler

适用于简单的单 API 调用场景，通过配置自动处理：
- API 调用
- 字段映射
- 日期范围计算
- 数据标准化

使用场景：
- GDP, CPI, PPI, PMI, Shibor, LPR, Money Supply 等宏观数据
- latest_trading_date 等简单查询
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from loguru import logger
import pandas as pd

from core.modules.data_source.data_source_handler import BaseDataSourceHandler
from core.modules.data_source.api_job import DataSourceTask, ApiJob
from core.utils.date.date_utils import DateUtils


class SimpleApiHandler(BaseDataSourceHandler):
    """
    简单 API Handler - 配置驱动的通用 Handler
    
    通过 mapping.json 中的配置自动处理简单的 API 调用场景。
    
    配置项（在 mapping.json 的 params 中）：
    - provider_name: Provider 名称（如 "tushare"）
    - method: API 方法名（如 "get_gdp"）
    - field_mapping: 字段映射规则（Dict[str, str] 或 Dict[str, Callable]）
    - date_format: 日期格式类型（"quarter" | "month" | "date" | "none"）
    - default_date_range: 默认日期范围计算规则
      - "years": int - 最近 N 年
      - "quarters": int - 最近 N 个季度
      - "months": int - 最近 N 个月
    - requires_date_range: 是否需要日期范围（默认 True）
    - custom_before_fetch: 自定义 before_fetch 逻辑（可选）
    - custom_normalize: 自定义 normalize 逻辑（可选）
    """
    
    # 类属性（必须定义，但会被配置覆盖）
    data_source = "simple_api"  # 会被实际数据源名称覆盖
    description = "简单 API Handler（配置驱动）"
    dependencies = []
    
    # 可选类属性
    requires_date_range = True  # 默认需要日期范围
    
    def __init__(self, schema, data_manager=None, definition=None):
        # 注意：data_source 会在 DataSourceManager 中设置，这里先调用 super
        super().__init__(schema, data_manager, definition)
        
        # 从配置中读取参数
        self.provider_name = self.get_param("provider_name", "tushare")
        self.method = self.get_param("method")
        self.field_mapping = self.get_param("field_mapping", {})
        self.date_format = self.get_param("date_format", "date")  # quarter | month | date | none
        self.default_date_range = self.get_param("default_date_range", {"years": 5})
        self.requires_date_range = self.get_param("requires_date_range", True)
        
        # 自定义逻辑（可选）
        self.custom_before_fetch = self.get_param("custom_before_fetch", None)
        self.custom_normalize = self.get_param("custom_normalize", None)
        
        if not self.method:
            raise ValueError(f"SimpleApiHandler 必须配置 method 参数")
    
    def set_data_source_name(self, name: str):
        """
        设置数据源名称（由 DataSourceManager 调用）
        """
        self.data_source = name
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        如果配置了 custom_before_fetch，则调用自定义逻辑
        否则使用默认的日期范围计算逻辑
        """
        context = context or {}
        
        # 如果有自定义逻辑，使用自定义逻辑
        if self.custom_before_fetch:
            if callable(self.custom_before_fetch):
                await self.custom_before_fetch(context)
            return
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            return
        
        # 如果不需要日期范围，直接返回
        if not self.requires_date_range:
            return
        
        # 从 data_manager 查询数据库获取最新日期（TODO: 待实现）
        if self.data_manager:
            try:
                # TODO: 查询数据库获取最新日期
                logger.debug("从数据库查询最新日期（待实现）")
            except Exception as e:
                logger.warning(f"查询数据库失败，使用默认日期范围: {e}")
        
        # 计算默认日期范围
        if "start_date" not in context or "end_date" not in context:
            start_date, end_date = self._calculate_default_date_range()
            context["start_date"] = start_date
            context["end_date"] = end_date
            logger.debug(f"使用默认日期范围: {start_date} 至 {end_date}")
    
    def _calculate_default_date_range(self) -> tuple[str, str]:
        """
        根据配置计算默认日期范围
        
        Returns:
            tuple: (start_date, end_date)
        """
        current_date = DateUtils.get_current_date_str()
        current_year = int(current_date[:4])
        current_month = int(current_date[4:6])
        
        if self.date_format == "quarter":
            # 季度格式：YYYYQ[1-4]
            if current_month <= 3:
                current_quarter = 1
            elif current_month <= 6:
                current_quarter = 2
            elif current_month <= 9:
                current_quarter = 3
            else:
                current_quarter = 4
            
            # 计算开始季度
            if "years" in self.default_date_range:
                years = self.default_date_range["years"]
                start_year = current_year - years
                start_quarter = 1
            elif "quarters" in self.default_date_range:
                quarters = self.default_date_range["quarters"]
                start_year = current_year
                start_quarter = current_quarter - quarters + 1
                while start_quarter < 1:
                    start_quarter += 4
                    start_year -= 1
            else:
                start_year = current_year - 5
                start_quarter = 1
            
            end_date = f"{current_year}Q{current_quarter}"
            start_date = f"{start_year}Q{start_quarter}"
            
        elif self.date_format == "month":
            # 月份格式：YYYYMM
            if "years" in self.default_date_range:
                years = self.default_date_range["years"]
                start_year = current_year - years
                start_month = 1
            elif "months" in self.default_date_range:
                months = self.default_date_range["months"]
                start_year = current_year
                start_month = current_month - months + 1
                while start_month < 1:
                    start_month += 12
                    start_year -= 1
            else:
                start_year = current_year - 3
                start_month = 1
            
            end_date = f"{current_year}{current_month:02d}"
            start_date = f"{start_year}{start_month:02d}"
            
        else:  # date_format == "date" or "none"
            # 日期格式：YYYYMMDD
            if "years" in self.default_date_range:
                years = self.default_date_range["years"]
                start_date = DateUtils.get_date_before_days(current_date, years * 365)
            elif "days" in self.default_date_range:
                days = self.default_date_range["days"]
                start_date = DateUtils.get_date_before_days(current_date, days)
            else:
                start_date = DateUtils.get_date_before_days(current_date, 5 * 365)
            
            end_date = current_date
        
        return start_date, end_date
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """
        生成获取数据的 Task
        
        逻辑：
        1. 从 context 获取参数
        2. 调用配置的 API 方法
        """
        context = context or {}
        
        # 构建 API 参数
        api_params = {}
        
        # 如果需要日期范围，从 context 获取
        if self.requires_date_range:
            start_date = context.get("start_date")
            end_date = context.get("end_date")
            
            if not start_date or not end_date:
                raise ValueError(f"{self.data_source} Handler 需要 start_date 和 end_date 参数")
            
            api_params["start_date"] = start_date
            api_params["end_date"] = end_date
        
        # 合并其他参数（从 context 或配置中）
        extra_params = self.get_param("extra_params", {})
        api_params.update(extra_params)
        
        # 从 context 中获取额外参数
        context_params = context.get("extra_params", {})
        api_params.update(context_params)
        
        # 请求参数已经在上游构造，避免在 debug 级别打印完整参数以减少日志噪音
        
        # 创建简单的单 API 调用 Task
        task = self.create_simple_task(
            provider_name=self.provider_name,
            method=self.method,
            params=api_params
        )
        
        return [task]
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据
        
        如果配置了 custom_normalize，则调用自定义逻辑
        否则使用默认的字段映射逻辑
        """
        # 如果有自定义逻辑，使用自定义逻辑
        if self.custom_normalize:
            if callable(self.custom_normalize):
                return await self.custom_normalize(task_results)
            return {"data": []}
        
        # 使用默认逻辑
        df = self.get_simple_result(task_results)
        
        if df is None or df.empty:
            logger.warning(f"{self.data_source} 数据查询返回空数据")
            return {"data": []}
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        # 字段映射和数据处理
        formatted = []
        
        for item in records:
            mapped = {}
            
            # 应用字段映射
            if self.field_mapping:
                for target_field, source_field in self.field_mapping.items():
                    if callable(source_field):
                        # 如果是函数，调用函数进行转换
                        mapped[target_field] = source_field(item)
                    elif isinstance(source_field, str):
                        # 如果是字符串，直接映射
                        value = item.get(source_field)
                        # 尝试转换为 float（如果是数字）
                        if value is not None:
                            if isinstance(value, (int, float)):
                                mapped[target_field] = float(value)
                            else:
                                mapped[target_field] = value
                        else:
                            # 如果值为 None，根据目标字段类型设置默认值
                            mapped[target_field] = 0.0 if target_field not in ['date', 'quarter', 'month'] else ''
                    else:
                        # 其他情况，直接使用原值
                        mapped[target_field] = item.get(source_field) if source_field in item else None
            else:
                # 如果没有字段映射，直接使用原始数据
                mapped = item.copy()
            
            # 只保留有效的记录
            if mapped:
                formatted.append(mapped)
        
        logger.info(f"✅ {self.data_source} 数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }

