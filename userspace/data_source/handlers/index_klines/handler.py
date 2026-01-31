"""
指数 K 线 Handler（index_klines）

从 Tushare 获取指数 K 线数据（日线/周线/月线），为每个指数和周期创建 ApiJob，写入 sys_index_klines。
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper


class IndexKlinesHandler(BaseHandler):
    """
    指数 K 线 Handler，绑定表 sys_index_klines。
    为每个指数和周期创建 ApiJob，全部获取后一起 normalize 并入库。
    """

    def __init__(
        self,
        data_source_key: str,
        schema,
        config,
        providers: Dict[str, BaseProvider],
        depend_on_data_source_names: List[str] = None,
    ):
        super().__init__(data_source_key, schema, config, providers, depend_on_data_source_names or [])
        from core.infra.project_context.config_manager import ConfigManager
        self.index_list = ConfigManager.load_benchmark_stock_index_list()

    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """为每个指数和周期创建 ApiJob。"""
        api_map = {api.api_name: api for api in apis}
        term_to_api = {
            "daily": "daily_kline",
            "weekly": "weekly_kline",
            "monthly": "monthly_kline",
        }
        expanded_apis = []
        for index_info in self.index_list:
            index_id = index_info["id"]
            for term, api_name in term_to_api.items():
                base_api = api_map.get(api_name)
                if not base_api:
                    continue
                new_api = ApiJob(
                    api_name=base_api.api_name,
                    provider_name=base_api.provider_name,
                    method=base_api.method,
                    params={**base_api.params, "ts_code": index_id},
                    api_params=base_api.api_params,
                    depends_on=base_api.depends_on,
                    rate_limit=base_api.rate_limit,
                    job_id=f"{index_id}_{term}",
                )
                expanded_apis.append(new_api)
        logger.info(f"✅ 为 {len(expanded_apis)} 个指数和周期生成了指数K线数据获取任务")
        return expanded_apis

    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]) -> Dict[str, Any]:
        """基于基类分组结果，追加 id 和 term 字段。"""
        grouped = super().on_after_fetch(context, fetched_data, apis)
        term_map = {"daily_kline": "daily", "weekly_kline": "weekly", "monthly_kline": "monthly"}
        unified: Dict[str, Dict[str, Any]] = {}
        for api_name, per_index_data in (grouped or {}).items():
            if not isinstance(per_index_data, dict):
                continue
            term = term_map.get(api_name)
            if not term:
                unified[api_name] = per_index_data
                continue
            bucket = {}
            for index_id, raw in per_index_data.items():
                records = DataSourceHandlerHelper.result_to_records(raw)
                if not records:
                    continue
                records = DataSourceHandlerHelper.add_constant_fields(records, id=index_id, term=term)
                bucket[str(index_id)] = records
            unified[api_name] = bucket
        return unified

    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤无效记录。"""
        if not mapped_records:
            return mapped_records
        return self.filter_records_by_required_fields(mapped_records, required_fields=["date"])

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        return normalized_data
