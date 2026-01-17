"""
滚动刷新 Handler - 配置驱动的通用 Handler，支持滚动刷新机制

适用于简单的单 API 宏观数据场景，通过配置自动处理：
- API 调用
- 字段映射
- 滚动刷新策略（每次运行都刷新最近 N 个时间单位的数据，确保数据一致性）
- 数据标准化

使用场景：
- GDP（季度数据，滚动刷新最近 4 个季度）
- Shibor, LPR（日期数据，滚动刷新最近 30 天）

注意：如果需要合并多个 API 的数据（如 Price Indexes），请使用独立的定制化 Handler
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from loguru import logger
import pandas as pd

from core.modules.data_source.data_source_handler import BaseDataSourceHandler
from core.modules.data_source.api_job import DataSourceTask, ApiJob
from core.utils.date.date_utils import DateUtils


class RollingHandler(BaseDataSourceHandler):
    """
    滚动刷新 Handler - 配置驱动的通用 Handler
    
    通过 mapping.json 中的配置自动处理宏观数据的 API 调用场景。
    支持滚动刷新机制：每次运行都刷新最近 N 个时间单位的数据，确保数据一致性。
    
    配置项（在 mapping.json 的 params 中）：
    - provider_name: Provider 名称（如 "tushare"）
    - method: API 方法名（如 "get_gdp"）
    - field_mapping: 字段映射规则（Dict[str, str] 或 Dict[str, Callable]）
    - date_format: 日期格式类型（"quarter" | "month" | "date" | "none"）
    - default_date_range: 默认日期范围计算规则（用于首次运行或数据库为空时）
      - "years": int - 最近 N 年
      - "quarters": int - 最近 N 个季度
      - "months": int - 最近 N 个月
      - "days": int - 最近 N 天
    - rolling_periods: 滚动刷新周期数（根据 date_format 自动识别单位）
      - 如果 date_format="quarter": 滚动刷新最近 N 个季度（默认 4）
      - 如果 date_format="month": 滚动刷新最近 N 个月（默认 12）
      - 如果 date_format="date": 滚动刷新最近 N 天（默认 30）
    - requires_date_range: 是否需要日期范围（默认 True）
    - table_name: 数据库表名（用于查询最新日期，默认使用 data_source 名称）
    - date_field: 数据库日期字段名（默认根据 date_format 自动识别：quarter/date）
    """
    
    # 类属性（必须定义，但会被配置覆盖）
    data_source = "rolling"  # 会被实际数据源名称覆盖
    description = "滚动刷新 Handler（配置驱动）"
    dependencies = []
    
    # 可选类属性
    requires_date_range = True  # 默认需要日期范围
    
    def __init__(self, schema, data_manager=None, definition=None):
        # 注意：data_source 会在 DataSourceManager 中设置，这里先调用 super
        super().__init__(schema, data_manager, definition)
        
        # 从配置中读取参数
        # 优先从 handler_config 读取，如果没有则从 provider_config.apis[0] 读取
        provider_config = self.get_provider_config()
        if provider_config and provider_config.apis and len(provider_config.apis) > 0:
            # 从第一个 API 配置中读取
            first_api = provider_config.apis[0]
            self.provider_name = self.get_param("provider_name") or first_api.provider_name
            self.method = self.get_param("method") or first_api.method
            self.field_mapping = self.get_param("field_mapping") or first_api.field_mapping or {}
        else:
            # 从 handler_config 读取
            self.provider_name = self.get_param("provider_name", "tushare")
            self.method = self.get_param("method")
            self.field_mapping = self.get_param("field_mapping", {})
        
        self.date_format = self.get_param("date_format", "date")  # quarter | month | date | none
        self.default_date_range = self.get_param("default_date_range", {"years": 5})
        self.rolling_periods = self.get_param("rolling_periods", None)  # 滚动刷新周期数
        self.requires_date_range = self.get_param("requires_date_range", True)
        self.table_name = self.get_param("table_name", None)  # 数据库表名，默认使用 data_source
        self.date_field = self.get_param("date_field", None)  # 数据库日期字段名
        
        # 自定义逻辑（可选）
        self.custom_before_fetch = self.get_param("custom_before_fetch", None)
        self.custom_normalize = self.get_param("custom_normalize", None)
        
        # 验证配置
        if not self.method:
            raise ValueError(f"RollingHandler 必须配置 method 参数（在 handler_config 或 provider_config.apis[0] 中）")
        
        # 设置默认滚动周期（如果未配置）
        if self.rolling_periods is None:
            if self.date_format == "quarter":
                self.rolling_periods = 4  # 默认滚动刷新最近 4 个季度
            elif self.date_format == "month":
                self.rolling_periods = 12  # 默认滚动刷新最近 12 个月
            elif self.date_format == "date":
                self.rolling_periods = 30  # 默认滚动刷新最近 30 天
            else:
                self.rolling_periods = 0  # 不需要滚动刷新
    
    def set_data_source_name(self, name: str):
        """
        设置数据源名称（由 DataSourceManager 调用）
        """
        self.data_source = name
        # 如果未配置 table_name，使用 data_source 名称
        if self.table_name is None:
            self.table_name = name
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        实现滚动刷新策略：
        1. 如果数据库为空：使用默认日期范围
        2. 如果数据库不为空：
           - 计算最新日期距离当前的时间间隔
           - 如果间隔 <= rolling_periods：滚动刷新最近 rolling_periods 个时间单位
           - 如果间隔 > rolling_periods：从最新日期开始追赶（历史追赶）
        """
        if context is None:
            context = {}
        
        # 如果有自定义逻辑，使用自定义逻辑
        if self.custom_before_fetch:
            if callable(self.custom_before_fetch):
                await self.custom_before_fetch(context)
            return context
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return context
        
        # 如果不需要日期范围，直接返回
        if not self.requires_date_range:
            return context
        
        # 获取当前日期/季度/月份
        current_date = DateUtils.get_current_date_str()
        current_value = self._get_current_value(current_date)
        
        # 从 data_manager 查询数据库获取最新日期
        latest_value = None
        if self.data_manager and self.rolling_periods > 0:
            try:
                model = self.data_manager.get_table(self.table_name)
                if model:
                    latest_record = model.load_latest()
                    if latest_record:
                        # 根据 date_format 获取日期字段
                        date_field = self.date_field or self._get_default_date_field()
                        latest_value = latest_record.get(date_field, '')
            except Exception as e:
                logger.warning(f"查询数据库失败: {e}")
        
        # 计算需要更新的日期范围
        if not latest_value:
            # 数据库为空：使用默认日期范围
            start_date, end_date = self._calculate_default_date_range()
            context["start_date"] = start_date
            context["end_date"] = end_date
            logger.info(f"数据库为空，使用默认日期范围: {start_date} 至 {end_date}")
        else:
            # 数据库不为空：计算时间间隔
            period_diff = self._calculate_period_diff(latest_value, current_value)
            
            if period_diff <= self.rolling_periods:
                # 间隔 <= rolling_periods：滚动刷新最近 rolling_periods 个时间单位
                start_value = self._subtract_periods(current_value, self.rolling_periods)
                start_date = self._format_value(start_value)
                end_date = self._format_value(current_value)
                context["start_date"] = start_date
                context["end_date"] = end_date
                logger.info(f"滚动刷新最近 {self.rolling_periods} 个{self._get_period_unit()}s: {start_date} 至 {end_date}（数据库最新: {latest_value}）")
            else:
                # 间隔 > rolling_periods：从最新日期开始追赶
                start_value = self._add_one_period(latest_value)
                start_date = self._format_value(start_value)
                end_date = self._format_value(current_value)
                context["start_date"] = start_date
                context["end_date"] = end_date
                logger.info(f"历史追赶: {start_date} 至 {end_date}（数据库最新: {latest_value}，落后 {period_diff} 个{self._get_period_unit()}s）")
        
        return context
    
    def _get_default_date_field(self) -> str:
        """根据 date_format 获取默认日期字段名"""
        if self.date_format == "quarter":
            return "quarter"
        elif self.date_format == "month":
            return "date"  # price_indexes 使用 date 字段存储月份
        else:
            return "date"
    
    def _get_current_value(self, current_date: str):
        """根据 date_format 获取当前值"""
        if self.date_format == "quarter":
            current_year = int(current_date[:4])
            current_month = int(current_date[4:6])
            if current_month <= 3:
                return (current_year, 1)
            elif current_month <= 6:
                return (current_year, 2)
            elif current_month <= 9:
                return (current_year, 3)
            else:
                return (current_year, 4)
        elif self.date_format == "month":
            return (int(current_date[:4]), int(current_date[4:6]))
        else:  # date_format == "date"
            return current_date
    
    def _parse_value(self, value: str):
        """解析日期值"""
        if self.date_format == "quarter":
            # YYYYQ[1-4]
            year = int(value[:4])
            quarter = int(value[5])
            return (year, quarter)
        elif self.date_format == "month":
            # YYYYMM
            return (int(value[:4]), int(value[4:6]))
        else:  # date_format == "date"
            # YYYYMMDD
            return value
    
    def _format_value(self, value) -> str:
        """格式化日期值"""
        if self.date_format == "quarter":
            year, quarter = value
            return f"{year}Q{quarter}"
        elif self.date_format == "month":
            year, month = value
            return f"{year}{month:02d}"
        else:  # date_format == "date"
            return value
    
    def _calculate_period_diff(self, latest_value: str, current_value) -> int:
        """计算两个日期之间的周期差"""
        latest = self._parse_value(latest_value)
        current = current_value  # current_value 已经是解析后的格式（元组或字符串）
        
        if self.date_format == "quarter":
            latest_year, latest_quarter = latest
            current_year, current_quarter = current
            return (current_year - latest_year) * 4 + (current_quarter - latest_quarter)
        elif self.date_format == "month":
            latest_year, latest_month = latest
            current_year, current_month = current
            return (current_year - latest_year) * 12 + (current_month - latest_month)
        else:  # date_format == "date"
            # latest 和 current 都是字符串格式的日期
            latest_date = DateUtils.parse_yyyymmdd(latest)
            current_date = DateUtils.parse_yyyymmdd(current)
            return (current_date - latest_date).days
    
    def _subtract_periods(self, value, periods: int):
        """减去 N 个周期"""
        if self.date_format == "quarter":
            year, quarter = value
            quarter -= periods - 1
            while quarter < 1:
                quarter += 4
                year -= 1
            return (year, quarter)
        elif self.date_format == "month":
            year, month = value
            month -= periods - 1
            while month < 1:
                month += 12
                year -= 1
            return (year, month)
        else:  # date_format == "date"
            # value 已经是字符串格式的日期
            date = DateUtils.parse_yyyymmdd(value)
            new_date = date - timedelta(days=periods - 1)
            return DateUtils.format_to_yyyymmdd(new_date)
    
    def _add_one_period(self, latest_value: str):
        """添加一个周期（用于历史追赶）"""
        latest = self._parse_value(latest_value)
        
        if self.date_format == "quarter":
            year, quarter = latest
            quarter += 1
            if quarter > 4:
                quarter = 1
                year += 1
            return (year, quarter)
        elif self.date_format == "month":
            year, month = latest
            month += 1
            if month > 12:
                month = 1
                year += 1
            return (year, month)
        else:  # date_format == "date"
            # latest 已经是字符串格式的日期
            date = DateUtils.parse_yyyymmdd(latest)
            new_date = date + timedelta(days=1)
            return DateUtils.format_to_yyyymmdd(new_date)
    
    def _get_period_unit(self) -> str:
        """获取周期单位名称"""
        if self.date_format == "quarter":
            return "quarter"
        elif self.date_format == "month":
            return "month"
        else:
            return "day"
    
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
        
        支持单 API 或多 API 场景
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
        
        # 使用默认逻辑：单 API 场景
        df = self.get_simple_result(task_results)
        
        if df is None or df.empty:
            logger.warning(f"{self.data_source} 数据查询返回空数据")
            return {"data": []}
        
        # 转换为字典列表并应用字段映射
        records = df.to_dict('records')
        formatted = self._apply_field_mapping(records)
        
        logger.info(f"✅ {self.data_source} 数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }
    
    def _apply_field_mapping(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用字段映射"""
        formatted = []
        
        for item in records:
            mapped = {}
            
            # 应用字段映射
            if self.field_mapping:
                for target_field, source_field in self.field_mapping.items():
                    if callable(source_field):
                        mapped[target_field] = source_field(item)
                    elif isinstance(source_field, str):
                        value = item.get(source_field)
                        if value is not None:
                            if isinstance(value, (int, float)):
                                mapped[target_field] = float(value)
                            else:
                                mapped[target_field] = value
                        else:
                            mapped[target_field] = 0.0 if target_field not in ['date', 'quarter', 'month'] else ''
                    else:
                        mapped[target_field] = item.get(source_field) if source_field in item else None
            else:
                mapped = item.copy()
            
            if mapped:
                formatted.append(mapped)
        
        return formatted
    
    async def after_normalize(self, normalized_data: Dict[str, Any], context: Dict[str, Any] = None):
        """
        标准化后处理：保存数据到数据库
        """
        context = context or {}
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过数据保存")
            return
        
        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法保存数据")
            return
        
        # 验证数据格式
        data_list = self._validate_data_for_save(normalized_data)
        if not data_list:
            logger.debug(f"{self.data_source} 数据为空，无需保存")
            return
        
        try:
            # 清理 NaN 值
            from core.infra.db.helpers.db_helpers import DBHelper
            data_list = DBHelper.clean_nan_in_list(data_list, default=0.0)
            
            # 保存数据
            model = self.data_manager.get_table(self.table_name)
            if model:
                # 确定主键字段
                date_field = self.date_field or self._get_default_date_field()
                
                # 使用 replace 方法保存（自动去重）
                # 优先使用 Model 的专门保存方法（如 save_gdp_data, save_shibor_data）
                save_method_name = f"save_{self.data_source}_data"
                if hasattr(model, save_method_name):
                    save_method = getattr(model, save_method_name)
                    count = save_method(data_list)
                else:
                    # 否则使用通用的 replace 方法
                    count = model.replace(data_list, unique_keys=[date_field])
                
                logger.info(f"✅ {self.data_source} 数据保存完成，共 {count} 条记录")
            else:
                logger.error(f"未找到 {self.table_name} Model，无法保存数据")
        except Exception as e:
            logger.error(f"❌ 保存 {self.data_source} 数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
