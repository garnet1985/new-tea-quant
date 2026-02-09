"""
企业财务数据 Handler

从 Tushare 获取企业财务指标数据（季度）。滚动窗口、批次轮转由框架处理。
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.normalization import normalization_helper as nh
from core.utils.date.date_utils import DateUtils


class CorporateFinanceHandler(BaseHandler):
    """企业财务数据 Handler：季度数据（YYYYQ[1-4]），滚动窗口 + 批次轮转由框架处理。"""

    CACHE_KEY = "corporate_finance_batch_offset"
    BATCH_AMOUNT = 10
    MIN_BATCH_SIZE = 1
    MAX_BATCH_SIZE = 450
    
    def __init__(
        self,
        data_source_key: str,
        schema,
        config: DataSourceConfig,
        providers: Dict[str, BaseProvider],
        depend_on_data_source_names: List[str] = None,
    ):
        super().__init__(data_source_key, schema, config, providers, depend_on_data_source_names or [])
    
    def on_build_job_payload(
        self,
        entity_info: Any,
        apis: List[ApiJob],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """注入 ts_code 到每个 API job。"""
        entity_id = entity_info.get("id") if isinstance(entity_info, dict) else str(entity_info)
        if not entity_id:
            return None
        for job in apis:
            job.params["ts_code"] = str(entity_id)
        return str(entity_id)
    
    def on_prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """通过环形切片 stock_list 实现批次轮转。"""
        context = super().on_prepare_context(context)
        all_stocks = context["dependencies"]["stock_list"]
        if not all_stocks:
            return context

        data_manager = context["data_manager"]
        try:
            cache_row = data_manager.db_cache.get(self.CACHE_KEY) or {}
            batch_offset = int(cache_row.get("value") or 0)
        except Exception:
            batch_offset = 0

        L = len(all_stocks)
        batch_size = max(self.MIN_BATCH_SIZE, min(self.MAX_BATCH_SIZE, L // self.BATCH_AMOUNT))
        indices = [(batch_offset + i) % L for i in range(batch_size)]
        selected_stocks = [all_stocks[i] for i in indices]
        new_offset = (batch_offset + batch_size) % L

        context["stock_list"] = selected_stocks
        try:
            data_manager.db_cache.set(self.CACHE_KEY, str(new_offset))
        except Exception:
            pass
        logger.info(f"✅ 批次选择完成：从 {len(all_stocks)} 只股票中选择 {len(selected_stocks)} 只")
        return context

    def on_after_single_api_job_bundle_complete(
        self, context: Dict[str, Any], job_bundle: Any, fetched_data: Dict[str, Any]
    ):
        """标准化并保存该股票的企业财务数据。"""
        stock_id = job_bundle.bundle_id.replace("corporate_finance_batch_", "")
        job_id = job_bundle.apis[0].job_id or job_bundle.apis[0].api_name
        result = fetched_data.get(job_id)
        if result is None:
            return fetched_data

        normalized = self._normalize_single_stock_data(context, result, stock_id)
        if not normalized["data"]:
            return fetched_data

        if not context.get("is_dry_run"):
            self._system_save(normalized)
            logger.info(f"✅ [单股票保存] {stock_id}: {len(normalized['data'])} 条企业财务记录")
        return fetched_data
    
    def _normalize_single_stock_data(
        self, context: Dict[str, Any], result: Any, stock_id: str
    ) -> Dict[str, Any]:
        """字段映射 + end_date -> quarter 转换，按 quarter 去重保留 end_date 最大的。"""
        records = nh.result_to_records(result)
        if not records:
            return {"data": []}

        records = self.clean_nan_in_records(records, default=None)
        api_cfg = context["config"].get_apis()["finance_data"]
        result_mapping = api_cfg.result_mapping
        mapped_records = nh.apply_field_mapping(records, result_mapping)

        quarter_records = {}
        for record in mapped_records:
            end_date = str(record.get("end_date", "")).replace("-", "")
            if len(end_date) != 8:
                continue
            quarter = DateUtils.date_to_quarter(end_date)
            if not quarter:
                continue
            existing = quarter_records.get(quarter)
            if existing is None or end_date > str(existing.get("end_date", "")).replace("-", ""):
                quarter_records[quarter] = record

        formatted = []
        for quarter, record in quarter_records.items():
            record["id"] = stock_id
            record["quarter"] = quarter
            record.pop("end_date", None)
            formatted.append(record)
        return {"data": formatted}
