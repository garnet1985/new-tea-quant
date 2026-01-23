"""
股指指标 Handler

从 Tushare 获取指数 K 线数据（日线/周线/月线）
为每个指数和周期创建 ApiJob，全部获取后一起 normalize 并入库
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper


class StockIndexIndicatorHandler(BaseHandler):
    """
    股指指标 Handler
    
    为每个指数和周期创建 ApiJob，全部获取后一起 normalize 并入库
    
    配置（在 config.json 中）：
    - renew_mode: "incremental"
    - date_format: "day"
    - index_list: [...] (指数列表)
    - apis: {...} (包含 daily_kline, weekly_kline, monthly_kline API 配置)
    """
    
    def __init__(self, data_source_name: str, schema, config, providers: Dict[str, BaseProvider]):
        super().__init__(data_source_name, schema, config, providers)
        # 指数列表来源：统一从 ConfigManager 的 benchmark_stock_index_list 读取，
        # 用户可在 userspace/config/data.json 覆盖默认值。
        from core.infra.project_context.config_manager import ConfigManager
        self.index_list = ConfigManager.load_benchmark_stock_index_list()
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：为每个指数和周期创建 ApiJob
        
        使用基类的统一日期范围，不需要为每个周期计算不同的结束日期
        
        Args:
            context: 执行上下文
            apis: 原始 ApiJob 列表（从 config 构建，包含 daily_kline, weekly_kline, monthly_kline）
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表（每个指数和周期一个 ApiJob）
        """
        # 构建 API name 到 base_api 的映射
        api_map = {api.api_name: api for api in apis}
        
        # 周期到 API name 的映射
        term_to_api = {
            "daily": "daily_kline",
            "weekly": "weekly_kline",
            "monthly": "monthly_kline"
        }
        
        expanded_apis = []
        
        # 为每个指数和周期创建 ApiJob
        # 日期范围由基类统一计算并注入，这里只需要设置 ts_code
        for index_info in self.index_list:
            index_id = index_info['id']
            
            for term, api_name in term_to_api.items():
                base_api = api_map.get(api_name)
                if not base_api:
                    continue
                
                # 创建 ApiJob，日期范围由基类统一注入
                new_api = ApiJob(
                    api_name=base_api.api_name,
                    provider_name=base_api.provider_name,
                    method=base_api.method,
                    params={
                        **base_api.params,
                        "ts_code": index_id,
                    },
                    api_params=base_api.api_params,
                    depends_on=base_api.depends_on,
                    rate_limit=base_api.rate_limit,
                    job_id=f"{index_id}_{term}",
                )
                expanded_apis.append(new_api)
        
        logger.info(f"✅ 为 {len(expanded_apis)} 个指数和周期生成了指数K线数据获取任务")
        
        return expanded_apis
    
    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]) -> Dict[str, Any]:
        """
        抓取完成后的预处理钩子：基于基类的统一分组结果，追加 id 和 term 字段。

        - 基类会根据 config.apis[api_name].group_by = "ts_code"，先将 {job_id: result}
          转换为 {api_name: {index_id: raw_result}} 的统一格式；
        - 本方法只关心业务字段补充：在原始 records 上追加 schema 所需的 id（指数代码）和
          term（daily/weekly/monthly）字段，然后仍然按统一格式返回。
        """
        # 先让基类按 group_by=ts_code 分好组
        grouped = super().on_after_fetch(context, fetched_data, apis)

        term_map: Dict[str, str] = {
            "daily_kline": "daily",
            "weekly_kline": "weekly",
            "monthly_kline": "monthly",
        }

        unified: Dict[str, Dict[str, Any]] = {}

        for api_name, per_index_data in (grouped or {}).items():
            if not isinstance(per_index_data, dict):
                continue

            term = term_map.get(api_name)
            if not term:
                # 未知周期的 API，直接透传
                unified[api_name] = per_index_data
                continue

            bucket: Dict[str, Any] = {}

            for index_id, raw in per_index_data.items():
                records = DataSourceHandlerHelper.result_to_records(raw)
                if not records:
                    continue

                records = DataSourceHandlerHelper.add_constant_fields(records, id=index_id, term=term)

                # 每个 index_id 仍然对应一份 raw_result（这里选择 list[dict]）
                bucket[str(index_id)] = records

            unified[api_name] = bucket

        return unified
    
    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        字段映射后的钩子：标准化日期格式
        
        Args:
            context: 执行上下文
            mapped_records: 已应用 field_mapping 的记录列表（已包含 id 和 term 字段）
            
        Returns:
            List[Dict[str, Any]]: 处理后的记录列表
        """
        if not mapped_records:
            return mapped_records

        # 使用通用日期归一工具，将 date 字段统一为 YYYYMMDD
        mapped_records = DataSourceHandlerHelper.normalize_date_field(mapped_records, field="date")

        # 过滤没有 date 字段的记录
        return self.filter_records_by_required_fields(mapped_records, required_fields=["date"])

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：数据清洗（NaN 清理），不负责保存。
        
        注意：data source 不负责 save，save 由上层（data_manager/service）自己处理。
        """
        # 可选：清洗 NaN 值
        return self.clean_nan_in_normalized_data(normalized_data, default=0.0)

