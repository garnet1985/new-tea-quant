"""
股指成分股权重 Handler

从 Tushare 获取指数成分股权重数据。

业务逻辑：
1. 调用 Tushare index_weight API
2. 为每个指数生成一个 ApiJob
3. 指数成分股不常变化，至少1个月才更新
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.utils.date.date_utils import DateUtils


class StockIndexIndicatorWeightHandler(BaseHandler):
    """
    股指成分股权重 Handler
    
    特点：
    - 为每个指数生成一个 ApiJob
    - 单API，简单mapping
    - 指数成分股不常变化，至少1个月才更新
    
    配置（在 config.json 中）：
    - renew_mode: "incremental"
    - date_format: "day"
    - index_list: [...] (指数列表)
    - apis: {...} (包含 index_weight API 配置)
    """
    
    def __init__(self, data_source_name: str, schema, config, providers: Dict[str, BaseProvider]):
        super().__init__(data_source_name, schema, config, providers)
        # 指数列表来源：统一从 ConfigManager 的 benchmark_stock_index_list 读取，
        # 用户可在 userspace/config/data.json 覆盖默认值。
        from core.infra.project_context.config_manager import ConfigManager
        self.index_list = ConfigManager.load_benchmark_stock_index_list()
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：为每个指数创建 ApiJob
        
        Args:
            context: 执行上下文
            apis: 原始 ApiJob 列表（从 config 构建）
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表（每个指数一个 ApiJob）
        """
        # 从 context 获取日期范围
        end_date = context.get("end_date")
        if not end_date:
            # 获取最新交易日
            latest_trading_date = context.get("latest_completed_trading_date")
            if not latest_trading_date:
                data_manager = context.get("data_manager")
                if data_manager:
                    try:
                        latest_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
                    except Exception as e:
                        logger.warning(f"获取最新交易日失败: {e}")
                        latest_trading_date = DateUtils.get_current_date_str()
                else:
                    latest_trading_date = DateUtils.get_current_date_str()
            
            # 实际结束日期是前一个交易日
            end_date = DateUtils.get_date_before_days(latest_trading_date, 1)
            context["end_date"] = end_date
        
        # 从数据库查询每个指数的最新日期
        index_latest_dates = {}  # {index_id: latest_date}
        data_manager = context.get("data_manager")
        if data_manager:
            try:
                index_latest_dates = data_manager.index.load_latest_weights()
            except Exception as e:
                logger.warning(f"查询数据库失败: {e}")
        
        context["index_latest_dates"] = index_latest_dates
        
        # 为每个指数创建 ApiJob
        expanded_apis = []
        base_api = apis[0] if apis else None  # 假设只有一个 base API
        
        if not base_api:
            logger.warning("未找到 base API，无法创建指数 ApiJobs")
            return apis
        
        for index_info in self.index_list:
            index_id = index_info['id']
            index_name = index_info.get('name', index_id)
            
            # 计算开始日期
            latest_date = index_latest_dates.get(index_id)
            
            if latest_date:
                # 有历史记录，从最新日期+1开始（增量更新）
                start_date = DateUtils.get_date_after_days(latest_date, 1)
            else:
                # 无历史记录，使用默认起始日期
                from core.infra.project_context import ConfigManager
                start_date = ConfigManager.get_default_start_date()
            
            # 如果开始日期大于结束日期，跳过
            if start_date > end_date:
                continue
            
            # 复制 base_api 并修改参数
            new_api = ApiJob(
                api_name=base_api.api_name,
                provider_name=base_api.provider_name,
                method=base_api.method,
                params={
                    **base_api.params,
                    "index_code": index_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                api_params=base_api.api_params,
                depends_on=base_api.depends_on,
                rate_limit=base_api.rate_limit,
                job_id=f"{index_id}_weight",
            )
            expanded_apis.append(new_api)
        
        logger.info(f"✅ 为 {len(expanded_apis)} 个指数生成了成分股权重数据获取任务")
        
        return expanded_apis
    
    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]) -> Dict[str, Any]:
        """
        抓取后阶段钩子：基于基类的统一分组结果，追加指数 id 字段。

        - config.apis["index_weight"].group_by = "index_code"，基类会先将 {job_id: result}
          转换为 {"index_weight": {index_id: raw_result}} 的统一格式；
        - 本方法只关心业务字段补充：在原始 records 上追加 schema 所需的 id（指数代码）字段，
          然后仍然按统一格式返回。
        """
        grouped = super().on_after_fetch(context, fetched_data, apis)

        unified: Dict[str, Dict[str, Any]] = {}

        for api_name, per_index_data in (grouped or {}).items():
            if not isinstance(per_index_data, dict):
                continue

            bucket: Dict[str, Any] = {}

            for index_id, raw in per_index_data.items():
                records = DataSourceHandlerHelper.result_to_records(raw)
                if not records:
                    continue

                records = DataSourceHandlerHelper.add_constant_fields(records, id=index_id)

                bucket[str(index_id)] = records

            unified[api_name] = bucket

        return unified
    
    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        字段映射后的钩子：过滤无效记录并确保类型正确
        
        Args:
            context: 执行上下文
            mapped_records: 已应用 field_mapping 的记录列表
            注意：日期标准化已在基类中自动处理（根据 config.date_format）
            
        Returns:
            List[Dict[str, Any]]: 处理后的记录列表
        """
        if not mapped_records:
            return mapped_records

        # 过滤没有 date 字段的记录
        mapped_records = self.filter_records_by_required_fields(mapped_records, required_fields=["date"])

        # 确保 weight 是 float 类型
        mapped_records = self.ensure_float_field(mapped_records, field="weight", default=0.0)

        logger.info(f"✅ 股指成分股权重数据处理完成，共 {len(mapped_records)} 条记录")
        return mapped_records
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：数据清洗（NaN 清理）已在基类中自动处理，这里直接返回。
        
        注意：data source 不负责 save，save 由上层（data_manager/service）自己处理。
        """
        # 基类已自动清洗 NaN，直接返回
        return normalized_data
