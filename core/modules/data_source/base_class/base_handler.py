from typing import Any, Dict, List

from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.data_class.schema import DataSourceSchema
from core.modules.data_source.data_class.task import DataSourceTask


class BaseHandler:
    """
    Base Handler class
    """
    def __init__(self, data_source_name: str, schema: DataSourceSchema, config: DataSourceConfig, providers: Dict[str, BaseProvider]):
        self.context = {
            "data_source_name": data_source_name,
            "schema": schema,
            "config": config,
            "providers": providers,
        }
        self.apis = self._resolve_apis(self.context)
        self.fetch_tasks = self._resolve_tasks(self.context, self.apis)
        self.fetched_data = None
        self.normalized_data = None

    def execute(self):
        self._reset()
        self.fetch_tasks = self.on_before_fetch(self.context, self.apis, self.fetch_tasks)
        self.fetched_data = self.on_fetch(self.context, self.fetch_tasks)
        self.fetched_data = self.on_after_fetch(self.context, self.fetched_data, self.fetch_tasks)
        self.fetched_data = self.on_before_normalize(self.context, self.fetched_data, self.fetch_tasks)
        self.normalized_data = self.on_normalize(self.context, self.fetched_data)
        self.normalized_data = self.on_after_normalize(self.context,self.normalized_data)


    def _resolve_apis(self, context: Dict[str, Any]):
        # wrapper API into ApiJob
        api_conf = self.context.get("config").get("apis")
        return DataSourceHandlerHelper.build_api_jobs(api_conf)

    def _resolve_tasks(self, context: Dict[str, Any], apis: List[ApiJob]):
        # tuple sort for ApiJob instances based on dependencies
        # resolve rate limit for each step
        pass

    def _reset(self):
        self.fetched_data = None
        self.normalized_data = None


    # ================================
    # Hooks
    # ================================

    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob], fetch_tasks: List[DataSourceTask]):
        # 可重写，有默认行为
        return self.fetch_tasks

    def on_fetch(self, context: Dict[str, Any], fetch_tasks: List[DataSourceTask]):
        # execute tasks
        fetched_data = {}
        for task in fetch_tasks:
            result = task.execute()
            fetched_data = {
                **fetched_data,
                **result,
            }
        return fetched_data

    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], fetch_tasks: List[DataSourceTask]):
        # 可重写，有默认行为
        return fetched_data

    def on_before_normalize(self, context: Dict[str, Any], fetched_data: Dict[str, Any], fetch_tasks: List[DataSourceTask]):
        # 可重写，有默认行为
        pass

    def on_normalize(self, context: Dict[str, Any], fetched_data: Dict[str, Any]):
        # normalize data
        self._map_data_by_schema(fetched_data, self.context)
        pass

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]):
        # 可重写，有默认行为
        pass

    def _map_data_by_schema(self, context: Dict[str, Any], fetched_data: Dict[str, Any]):
        # map data by schema
        pass