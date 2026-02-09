"""
指数 K 线 Handler

从 Tushare 获取指数 K 线（日/周/月），写入 sys_index_klines。
与 stock_klines 逻辑一致：按 (id, term) 分组，支持 daily/weekly/monthly 独立追踪。
"""
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import pandas as pd

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_config import ApiConfig
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.utils.date.date_utils import DateUtils


class IndexKlinesHandler(BaseHandler):
    """指数 K 线 Handler，绑定表 sys_index_klines。逻辑与 stock_klines 一致。"""

    API_TO_TERM = {
        "daily_kline": "daily",
        "weekly_kline": "weekly",
        "monthly_kline": "monthly",
    }
    TERM_TO_NAME = {"daily": "日线", "weekly": "周线", "monthly": "月线"}

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
        """注入 ts_code 和 term 到每个 API job（term 来自 API 名称）。"""
        if isinstance(entity_info, dict):
            entity_id = entity_info.get("id")
        else:
            entity_id = str(entity_info) if entity_info else None
        if not entity_id:
            return None
        for job in apis:
            job.params = job.params or {}
            job.params["ts_code"] = str(entity_id)
            api_term = self.API_TO_TERM.get(job.api_name)
            if api_term:
                job.params["term"] = api_term
                job.job_id = f"{entity_id}_{api_term}"
        return str(entity_id)

    def on_after_build_jobs(
        self,
        context: Dict[str, Any],
        jobs: List[ApiJobBundle],
        entity_date_ranges: Dict[str, Tuple[str, str]]
    ) -> List[ApiJobBundle]:
        """与 stock_klines 一致：从 entity_date_ranges 构建 job bundles（按 index + term）。"""
        if jobs:
            merged = self._merge_index_jobs(jobs)
            if merged is not None:
                return merged
        if not entity_date_ranges:
            logger.warning("⚠️ [index_klines] entity_date_ranges 为空")
            return jobs or []
        return self._build_jobs_from_ranges(context, entity_date_ranges)

    def _parse_entity_date_ranges(
        self, entity_date_ranges: Dict[str, Tuple[str, str]]
    ) -> Dict[str, Dict[str, Tuple[str, str]]]:
        """解析 entity_date_ranges，将 "id::term" 转为按 index 分组的 {term: (start, end)}。"""
        result: Dict[str, Dict[str, Tuple[str, str]]] = {}
        for key, date_range in entity_date_ranges.items():
            if "::" not in key:
                index_id = key
                term = None
            else:
                parts = key.split("::")
                index_id = parts[0]
                term = parts[1] if len(parts) > 1 else None
            if not index_id:
                continue
            if index_id not in result:
                result[index_id] = {}
            if term:
                result[index_id][term] = date_range
            else:
                result[index_id]["default"] = date_range
        return result

    def _should_update_term(
        self, term: str, last_update: Optional[str], end_date: str
    ) -> bool:
        """检查某 term 是否需要更新。"""
        if not last_update:
            return True
        if term == "daily":
            return True
        if term == "weekly":
            days_diff = DateUtils.diff_days(last_update, end_date)
            return (days_diff // 7) >= 1
        if term == "monthly":
            from datetime import datetime
            latest_dt = datetime.strptime(last_update, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            month_diff = (end_dt.year - latest_dt.year) * 12 + (end_dt.month - latest_dt.month)
            if end_dt.day < latest_dt.day:
                month_diff -= 1
            return month_diff >= 1
        return True

    def _filter_apis_by_term_update_needs(
        self,
        apis_conf: Dict[str, ApiConfig],
        index_id: str,
        term_date_ranges: Dict[str, Tuple[str, str]],
        last_update_map: Dict[str, Optional[str]]
    ) -> Dict[str, ApiConfig]:
        """过滤需要更新的 API。"""
        filtered = {}
        for api_name, api_config in apis_conf.items():
            term = self.API_TO_TERM.get(api_name)
            if not term or term not in term_date_ranges:
                continue
            start_date, end_date = term_date_ranges[term]
            if not DateUtils.is_before(start_date, end_date):
                continue
            composite_key = f"{index_id}::{term}"
            last_update = last_update_map.get(composite_key)
            if not self._should_update_term(term, last_update, end_date):
                continue
            filtered[api_name] = api_config
        return filtered

    def _merge_index_jobs(self, jobs: List[ApiJobBundle]) -> Optional[List[ApiJobBundle]]:
        """合并同一指数的多个 term jobs 为一个 bundle。"""
        by_index: Dict[str, List[ApiJobBundle]] = {}
        for job in jobs:
            index_id = self._extract_index_id_from_bundle(job.bundle_id)
            if not index_id:
                continue
            if index_id not in by_index:
                by_index[index_id] = []
            by_index[index_id].append(job)
        if all(len(v) == 1 for v in by_index.values()):
            return None
        merged = []
        for index_id, job_list in by_index.items():
            if len(job_list) == 1:
                merged.append(job_list[0])
            else:
                all_apis = []
                for j in job_list:
                    all_apis.extend(j.apis or [])
                start_dates = [j.start_date for j in job_list if j.start_date]
                end_dates = [j.end_date for j in job_list if j.end_date]
                base = job_list[0]
                base_bid = base.bundle_id.split("::")[0] if "::" in (base.bundle_id or "") else base.bundle_id
                merged.append(ApiJobBundle(
                    bundle_id=base_bid or f"{self.get_key()}_batch_{index_id}",
                    apis=all_apis,
                    tuple_order_map=base.tuple_order_map,
                    start_date=min(start_dates) if start_dates else base.start_date,
                    end_date=max(end_dates) if end_dates else base.end_date,
                ))
        return merged

    def _build_jobs_from_ranges(
        self,
        context: Dict[str, Any],
        entity_date_ranges: Dict[str, Tuple[str, str]]
    ) -> List[ApiJobBundle]:
        """从 entity_date_ranges 构建 job bundles。"""
        term_ranges = self._parse_entity_date_ranges(entity_date_ranges)
        config = context.get("config")
        if not isinstance(config, DataSourceConfig):
            return []
        apis_conf = config.get_apis()
        entity_list = self._get_entity_list()
        last_update_map = context.get("_last_update_map", {})
        entity_key = "id"

        merged_jobs = []
        for entity_info in entity_list:
            if isinstance(entity_info, dict):
                index_id = entity_info.get(entity_key) or entity_info.get("id")
            else:
                index_id = str(entity_info) if entity_info else None
            if not index_id:
                continue
            index_id = str(index_id)
            tr = term_ranges.get(index_id)
            if not tr:
                continue
            filtered = self._filter_apis_by_term_update_needs(
                apis_conf, index_id, tr, last_update_map
            )
            if not filtered:
                continue
            all_starts = [dr[0] for dr in tr.values()]
            all_ends = [dr[1] for dr in tr.values()]
            date_range = (min(all_starts), max(all_ends))
            entity_for_build = {"id": index_id} if isinstance(entity_info, dict) else index_id
            job_bundle = self._build_job(entity_for_build, filtered, date_range)
            if job_bundle is None:
                continue
            self._set_term_date_ranges_for_apis(job_bundle.apis, tr)
            merged_jobs.append(job_bundle)

        logger.info(f"🔧 [index_klines] 构建完成: {len(merged_jobs)} 个 job bundles")
        return merged_jobs

    def _set_term_date_ranges_for_apis(
        self,
        apis: List[ApiJob],
        term_date_ranges: Dict[str, Tuple[str, str]]
    ) -> None:
        """为每个 API 设置对应 term 的日期范围。"""
        for api_job in apis:
            term = self.API_TO_TERM.get(api_job.api_name)
            if term and term in term_date_ranges:
                start_date, end_date = term_date_ranges[term]
                api_job.params = api_job.params or {}
                api_job.params["start_date"] = start_date
                api_job.params["end_date"] = end_date

    def on_after_single_api_job_bundle_complete(
        self,
        context: Dict[str, Any],
        job_bundle: ApiJobBundle,
        fetched_data: Dict[str, Any]
    ):
        """执行单个 bundle 后：处理并保存指数 K 线。"""
        index_id = self._extract_index_id_from_bundle(job_bundle.bundle_id)
        if not index_id:
            return fetched_data
        data_manager = context.get("data_manager")
        config = context.get("config")
        for api_job in job_bundle.apis or []:
            records = self._process_single_api_job(
                api_job, index_id, fetched_data, config
            )
            if records:
                self._save_index_kline_records(records, index_id, context, data_manager)
        return fetched_data

    def _process_single_api_job(
        self,
        api_job: ApiJob,
        index_id: str,
        fetched_data: Dict[str, Any],
        config: DataSourceConfig
    ) -> List[Dict[str, Any]]:
        """处理单个 API 的数据：提取、映射、添加 id/term。"""
        api_name = api_job.api_name
        term = self.API_TO_TERM.get(api_name)
        if not term:
            return []
        job_id = api_job.job_id or api_job.api_name
        raw = fetched_data.get(job_id)
        if raw is None:
            return []
        df = pd.DataFrame(raw) if not isinstance(raw, pd.DataFrame) else raw
        if df.empty:
            return []
        api_config = config.get_apis().get(api_name)
        result_mapping = api_config.result_mapping if api_config else {}
        records = df.to_dict("records")
        mapped = DataSourceHandlerHelper._apply_field_mapping(records, result_mapping)
        for r in mapped:
            r["id"] = index_id
            r["term"] = term
        return self.clean_nan_in_records(mapped, default=None)

    def _save_index_kline_records(
        self,
        records: List[Dict[str, Any]],
        index_id: str,
        context: Dict[str, Any],
        data_manager: Any
    ) -> None:
        """保存指数 K 线到 sys_index_klines。"""
        term = records[0].get("term", "unknown")
        term_name = self.TERM_TO_NAME.get(term, term)
        if context.get("is_dry_run"):
            logger.info(f"🔍 [DRY RUN] 指数 {index_id} {term_name} K 线: {len(records)} 条")
        else:
            model = data_manager.get_table("sys_index_klines")
            if model:
                model.save_records(records)
                logger.info(f"✅ [{index_id}] {term_name} 保存 {len(records)} 条")

    def _extract_index_id_from_bundle(self, bundle_id: str) -> Optional[str]:
        """从 bundle_id 提取指数 ID。"""
        if "_batch_" not in (bundle_id or ""):
            return None
        parts = (bundle_id or "").split("_batch_")
        suffix = parts[1] if len(parts) >= 2 else ""
        return suffix.split("::")[0] if suffix else None
