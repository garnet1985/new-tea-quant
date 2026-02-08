"""
指数 K 线 Handler

从 Tushare 获取指数 K 线（日/周/月），写入 sys_index_klines。
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper

TERM_TO_API = {"daily": "daily_kline", "weekly": "weekly_kline", "monthly": "monthly_kline"}
API_TO_TERM = {v: k for k, v in TERM_TO_API.items()}


class IndexKlinesHandler(BaseHandler):
    """指数 K 线 Handler，绑定表 sys_index_klines。"""

    def __init__(
        self,
        data_source_key: str,
        schema,
        config: DataSourceConfig,
        providers: Dict[str, BaseProvider],
        depend_on_data_source_names: List[str] = None,
    ):
        super().__init__(data_source_key, schema, config, providers, depend_on_data_source_names or [])
        from core.infra.project_context.config_manager import ConfigManager
        self.index_list = ConfigManager.load_benchmark_stock_index_list()

    def on_prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """注入 index_list 到 dependencies。"""
        context = super().on_prepare_context(context)
        context.setdefault("dependencies", {})["index_list"] = self.index_list
        return context

    def on_build_job_payload(
        self,
        entity_info: Any,
        apis: List[ApiJob],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """注入 ts_code 到每个 API job，并设置唯一 job_id 以便多 bundle 合并时正确分组。"""
        entity_id = entity_info.get("id") if isinstance(entity_info, dict) else str(entity_info)
        if not entity_id:
            return None
        for job in apis:
            job.params = job.params or {}
            job.params["ts_code"] = str(entity_id)
            term = API_TO_TERM.get(job.api_name)
            if term:
                job.job_id = f"{entity_id}_{term}"
        return str(entity_id)

    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]) -> Dict[str, Any]:
        """追加 id 和 term 字段。"""
        grouped = super().on_after_fetch(context, fetched_data, apis) or {}
        term_map = {"daily_kline": "daily", "weekly_kline": "weekly", "monthly_kline": "monthly"}
        unified = {}
        for api_name, per_index_data in grouped.items():
            if not isinstance(per_index_data, dict):
                continue
            term = term_map.get(api_name)
            if not term:
                unified[api_name] = per_index_data
                continue
            bucket = {}
            for index_id, raw in per_index_data.items():
                records = DataSourceHandlerHelper.result_to_records(raw)
                if records:
                    bucket[str(index_id)] = DataSourceHandlerHelper.add_constant_fields(records, id=index_id, term=term)
            unified[api_name] = bucket
        return unified

    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤无效记录。"""
        return self.filter_records_by_required_fields(mapped_records or [], required_fields=["date"])
