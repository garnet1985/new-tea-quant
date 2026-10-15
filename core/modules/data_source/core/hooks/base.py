"""用户数据源钩子。

引擎负责规划、抓取、写入和进度。这里只放一次更新里可以改的步骤。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_source.core.data_class.api_job import ApiJob
from core.modules.data_source.core.data_class.config import DataSourceConfig


class DataSourceHooks:
    """一次数据源更新的用户钩子。"""

    ds: Any

    def bind(self, handler: Any) -> None:
        self.ds = handler

    @property
    def context(self) -> Dict[str, Any]:
        return self.ds.context

    def on_prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if context.get("latest_completed_trading_date"):
            return context
        data_manager = context.get("data_manager")
        if not data_manager:
            return context
        try:
            context["latest_completed_trading_date"] = (
                data_manager.service.calendar.get_latest_completed_trading_date()
            )
        except Exception:
            pass
        return context

    def on_build_job_payload(
        self,
        entity_info: Any,
        apis: List[ApiJob],
        context: Dict[str, Any],
    ) -> Optional[str]:
        _ = apis
        if not entity_info:
            return None
        config: DataSourceConfig = context.get("config")
        if not config:
            return None
        group_fields = config.get_group_fields() if config else []
        if group_fields:
            entity_key_field = group_fields[0]
        else:
            entity_key_field = config.get_group_by_key()
        if not entity_key_field:
            return None
        entity_id = self.ds._extract_entity_id(entity_info, entity_key_field, context)
        return str(entity_id) if entity_id else None

    def on_after_build_jobs(
        self,
        context: Dict[str, Any],
        jobs: List[Any],
        entity_date_ranges: Dict[str, Tuple[str, str]],
    ) -> List[Any]:
        _ = (context, entity_date_ranges)
        return jobs

    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        _ = context
        return apis

    def enrich_result_for_batch(
        self, context: Dict[str, Any], job_bundle: Any, raw_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        _ = (context, job_bundle)
        return raw_result

    def bundle_to_frames(self, context: Dict[str, Any], job_bundle: Any, fetched_data: Dict[str, Any]):
        return self.ds._bundle_to_frames(context, job_bundle, fetched_data)

    def save_record_chunk(self, context: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
        self.ds._save_record_chunk(context, rows)

    def save_frames(self, context: Dict[str, Any], frames: List[Any]) -> None:
        self.ds._save_frames(context, frames)

    def on_after_fetch(
        self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]
    ):
        from core.modules.data_source.core.service.executor import fetched_data_helper as helper

        if helper.has_group_by_config(context, apis):
            return helper.build_grouped_fetched_data(context, fetched_data, apis)
        return helper.build_unified_fetched_data(context, fetched_data, apis)

    def on_after_mapping(
        self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        _ = context
        return mapped_records

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]):
        config = context.get("config")
        date_format = config.get_date_format() if config else ""
        default = 0.0 if date_format in ("day", "month") else None
        return self.clean_nan_in_normalized_data(normalized_data, default=default)

    def on_before_run(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        _ = context
        return None

    def on_before_save(
        self, context: Dict[str, Any], normalized_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        _ = (context, normalized_data)
        return None

    def on_bundle_execution_error(
        self, error: Exception, context: Dict[str, Any], apis: List[ApiJob]
    ) -> None:
        _ = (error, context, apis)

    @staticmethod
    def clean_nan_in_records(records: List[Dict[str, Any]], default: Any = None) -> List[Dict[str, Any]]:
        from core.modules.data_source.core.service.utils import record_utils

        return record_utils.clean_nan_in_records(records, default=default)

    @staticmethod
    def clean_nan_in_normalized_data(
        normalized_data: Dict[str, Any], default: Any = None
    ) -> Dict[str, Any]:
        from core.modules.data_source.core.service.utils import record_utils

        return record_utils.clean_nan_in_normalized_data(normalized_data, default=default)

    @staticmethod
    def filter_records_by_required_fields(
        records: List[Dict[str, Any]], required_fields: List[str]
    ) -> List[Dict[str, Any]]:
        from core.modules.data_source.core.service.utils import record_utils

        return record_utils.filter_records_by_required_fields(records, required_fields)

    @staticmethod
    def ensure_float_field(
        records: List[Dict[str, Any]], field: str, default: float = 0.0
    ) -> List[Dict[str, Any]]:
        from core.modules.data_source.core.service.utils import record_utils

        return record_utils.ensure_float_field(records, field, default=default)


__all__ = ["DataSourceHooks"]
