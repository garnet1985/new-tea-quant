"""
指数成分股权重 Handler（index_weight）

从 Tushare 获取指数成分股权重数据，为每个指数创建 ApiJob，写入 sys_index_weight。
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.utils.date.date_utils import DateUtils


class IndexWeightHandler(BaseHandler):
    """
    指数成分股权重 Handler，绑定表 sys_index_weight。
    为每个指数生成一个 ApiJob。
    """

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
        """注入 index_list 到 dependencies（与 index_klines 一致）。"""
        context = super().on_prepare_context(context)
        context.setdefault("dependencies", {})["index_list"] = self.index_list
        return context

    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """为每个指数创建 ApiJob。"""
        end_date = context.get("end_date")
        if not end_date:
            latest_trading_date = context.get("latest_completed_trading_date")
            if not latest_trading_date:
                latest_trading_date = context["data_manager"].service.calendar.get_latest_completed_trading_date()
            end_date = DateUtils.sub_days(latest_trading_date, 1)
            context["end_date"] = end_date

        data_manager = context["data_manager"]
        try:
            index_latest_dates = data_manager.index.load_latest_weights()
        except Exception:
            index_latest_dates = {}
        context["index_latest_dates"] = index_latest_dates

        if not apis:
            return apis
        # apis 可能是 ApiJobBundle 列表，取第一个 bundle 的 apis[0] 作为模板
        first = apis[0]
        base_api = first.apis[0] if hasattr(first, "apis") and first.apis else first
        if not base_api:
            return apis

        expanded_apis = []

        for index_info in self.index_list:
            index_id = index_info["id"]
            latest_date = index_latest_dates.get(index_id)
            if latest_date:
                start_date = DateUtils.add_days(latest_date, 1)
            else:
                from core.infra.project_context import ConfigManager
                start_date = ConfigManager.get_default_start_date()
            if start_date > end_date:
                continue
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
        """基于基类分组结果，追加指数 id 字段。"""
        grouped = super().on_after_fetch(context, fetched_data, apis)
        unified = {}
        for api_name, per_index_data in (grouped or {}).items():
            if not isinstance(per_index_data, dict):
                continue
            bucket = {}
            for index_id, raw in per_index_data.items():
                records = DataSourceHandlerHelper.result_to_records(raw)
                if not records:
                    continue
                records = DataSourceHandlerHelper.add_constant_fields(records, id=index_id)
                bucket[str(index_id)] = records
            unified[api_name] = bucket
        return unified

    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤无效记录。"""
        if not mapped_records:
            return mapped_records
        mapped_records = self.filter_records_by_required_fields(mapped_records, required_fields=["date"])
        logger.info(f"✅ 指数成分股权重数据处理完成，共 {len(mapped_records)} 条记录")
        return mapped_records

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        return normalized_data
