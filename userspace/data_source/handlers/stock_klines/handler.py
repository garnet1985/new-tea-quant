"""
统一的 K 线 Handler，处理 daily/weekly/monthly 三个周期。

通过钩子简化实现：
- _build_jobs: 为每个股票计算统一的日期范围（取所有周期中最小的 last_update）
- on_after_single_api_job_bundle_complete: 处理并保存数据
"""
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
import pandas as pd

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.data_class.api_config import ApiConfig
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.utils.date.date_utils import DateUtils


class KlineHandler(BaseHandler):
    """
    统一的 K 线 Handler，处理 daily/weekly/monthly 三个周期。
    
    通过钩子简化实现，避免复杂的自定义逻辑。
    """
    
    # API 名称到 term 的映射
    API_TO_TERM = {
        "daily_kline": "daily",
        "weekly_kline": "weekly",
        "monthly_kline": "monthly",
    }
    
    # term 到中文名称的映射（用于日志）
    TERM_TO_NAME = {
        "daily": "日线",
        "weekly": "周线",
        "monthly": "月线",
    }
    
    def on_build_job_payload(
        self,
        entity_info: Any,
        apis: List[ApiJob],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """构建 job payload：手动注入 ts_code 参数到每个 API job 的 params 中。"""
        entity_id = entity_info.get("id") if isinstance(entity_info, dict) else str(entity_info)
        if not entity_id:
            return None
        
        # 为每个 API job 手动注入 ts_code 参数
        for job in apis:
            job.params = job.params or {}
            job.params["ts_code"] = str(entity_id)
        
        return str(entity_id)
    
    def on_after_build_jobs(
        self, 
        context: Dict[str, Any], 
        jobs: List[ApiJobBundle],
        entity_date_ranges: Dict[str, Tuple[str, str]]
    ) -> List[ApiJobBundle]:
        """
        Jobs 构建完成后的钩子：合并同一股票的多个周期 jobs 为一个 bundle。
        
        由于配置使用了 keys: ["id", "term"]，框架会为每个股票的每个周期创建一个 job
        （因为 entity_date_ranges 的 key 是 "{stock_id}::{term}" 格式，框架无法匹配）。
        
        我们需要：
        1. 从 entity_date_ranges 中提取每个股票的日期范围（取所有周期中最小的 start_date 和最大的 end_date）
        2. 为每个股票创建一个包含所有周期 API 的 bundle
        """
        # 如果已经有 jobs，尝试合并同一股票的多个周期 jobs
        if jobs:
            merged_jobs = self._merge_stock_jobs(jobs)
            if merged_jobs is not None:
                return merged_jobs
        
        # 如果没有 jobs 或合并失败，从 entity_date_ranges 重新构建 jobs
        if not entity_date_ranges:
            logger.warning("⚠️ [kline] entity_date_ranges 为空，无法构建 jobs")
            return jobs or []
        
        return self._build_jobs_from_ranges(context, entity_date_ranges)
    
    def _should_update_term(
        self, 
        term: str, 
        last_update: Optional[str], 
        end_date: str
    ) -> bool:
        """
        检查某个 term 是否需要更新（基于时间间隔）。
        
        Args:
            term: 周期类型（daily/weekly/monthly）
            last_update: 上次更新时间（YYYYMMDD 格式）
            end_date: 结束日期（YYYYMMDD 格式）
        
        Returns:
            bool: 是否需要更新
        """
        if not last_update:
            # 没有历史数据，需要更新
            return True
        
        if term == "daily":
            # 日线：总是更新（框架已处理 renew_if_over_days）
            return True
        elif term == "weekly":
            # 周线：只有当时间间隔 >= 1 周时才更新
            days_diff = DateUtils.diff_days(last_update, end_date)
            return (days_diff // 7) >= 1
        elif term == "monthly":
            # 月线：只有当时间间隔 >= 1 个月时才更新
            from datetime import datetime
            latest_dt = datetime.strptime(last_update, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            year1, month1 = latest_dt.year, latest_dt.month
            year2, month2 = end_dt.year, end_dt.month
            month_diff = (year2 - year1) * 12 + (month2 - month1)
            # 如果天数不足，减一个月
            if end_dt.day < latest_dt.day:
                month_diff -= 1
            return month_diff >= 1
        
        return True
    
    def _parse_entity_date_ranges(
        self, 
        entity_date_ranges: Dict[str, Tuple[str, str]]
    ) -> Dict[str, Dict[str, Tuple[str, str]]]:
        """
        解析 entity_date_ranges，将复合 key "{stock_id}::{term}" 转换为按股票分组的字典。
        
        Args:
            entity_date_ranges: 框架返回的日期范围字典，key 可能是复合 key
        
        Returns:
            Dict[stock_id, Dict[term, (start_date, end_date)]]
        """
        stock_term_date_ranges: Dict[str, Dict[str, Tuple[str, str]]] = {}
        
        for composite_key, date_range in entity_date_ranges.items():
            if "::" not in composite_key:
                # 单字段分组的情况，使用整个 key 作为 stock_id
                stock_id = composite_key
                term = None
            else:
                # 提取 stock_id 和 term（复合 key 的格式："{stock_id}::{term}"）
                parts = composite_key.split("::")
                stock_id = parts[0]
                term = parts[1] if len(parts) > 1 else None
            
            if not stock_id:
                continue
            
            if stock_id not in stock_term_date_ranges:
                stock_term_date_ranges[stock_id] = {}
            
            if term:
                # 多字段分组：为每个 term 保存独立的日期范围
                stock_term_date_ranges[stock_id][term] = date_range
            else:
                # 单字段分组：使用 "default" 作为 key
                stock_term_date_ranges[stock_id]["default"] = date_range
        
        return stock_term_date_ranges
    
    def _filter_apis_by_term_update_needs(
        self,
        apis_conf: Dict[str, ApiConfig],
        stock_id: str,
        term_date_ranges: Dict[str, Tuple[str, str]],
        last_update_map: Dict[str, Optional[str]]
    ) -> Dict[str, Any]:
        """
        根据时间间隔过滤需要更新的 API。
        
        Args:
            apis_conf: Dict[str, ApiConfig]，来自 config.get_apis()
            stock_id: 股票 ID
            term_date_ranges: 该股票的各个 term 的日期范围
            last_update_map: 上次更新时间的映射
        
        Returns:
            过滤后的 Dict[str, ApiConfig]
        """
        filtered_apis_conf: Dict[str, ApiConfig] = {}
        
        for api_name, api_config in apis_conf.items():
            term = self.API_TO_TERM.get(api_name)
            if not term or term not in term_date_ranges:
                continue
            
            # 检查日期范围是否有效（start_date < end_date）
            term_start_date, term_end_date = term_date_ranges[term]
            if not DateUtils.is_before(term_start_date, term_end_date):
                continue
            
            # 检查时间间隔是否足够
            composite_key = f"{stock_id}::{term}"
            last_update = last_update_map.get(composite_key)
            
            if not self._should_update_term(term, last_update, term_end_date):
                continue
            
            # 时间间隔足够，保留这个 API
            filtered_apis_conf[api_name] = api_config
        
        return filtered_apis_conf
    
    def _merge_stock_jobs(self, jobs: List[ApiJobBundle]) -> Optional[List[ApiJobBundle]]:
        """
        合并同一股票的多个周期 jobs 为一个 bundle。
        
        Args:
            jobs: 原始的 job bundles 列表
        
        Returns:
            合并后的 job bundles 列表，如果不需要合并则返回 None
        """
        # 按股票 ID 分组 jobs
        stock_jobs: Dict[str, List[ApiJobBundle]] = {}
        
        for job in jobs:
            stock_id = self._extract_stock_id_from_bundle(job.bundle_id)
            if not stock_id:
                continue
            
            if stock_id not in stock_jobs:
                stock_jobs[stock_id] = []
            stock_jobs[stock_id].append(job)
        
        # 如果每个股票只有一个 job，说明已经合并了，不需要处理
        if all(len(job_list) == 1 for job_list in stock_jobs.values()):
            return None
        
        # 合并每个股票的多个 jobs
        merged_jobs: List[ApiJobBundle] = []
        for stock_id, stock_job_list in stock_jobs.items():
            if len(stock_job_list) == 1:
                merged_jobs.append(stock_job_list[0])
            else:
                # 合并多个 jobs：合并所有 API，统一日期范围
                base_job = stock_job_list[0]
                all_apis = []
                for job in stock_job_list:
                    all_apis.extend(job.apis)
                
                # 取最早的 start_date 和最晚的 end_date
                start_dates = [job.start_date for job in stock_job_list if job.start_date]
                end_dates = [job.end_date for job in stock_job_list if job.end_date]
                
                unified_start_date = min(start_dates) if start_dates else base_job.start_date
                unified_end_date = max(end_dates) if end_dates else base_job.end_date
                
                # 创建新的 bundle_id（移除 term 后缀）
                base_bundle_id = base_job.bundle_id
                if "::" in base_bundle_id:
                    base_bundle_id = base_bundle_id.split("::")[0]
                
                merged_bundle = ApiJobBundle(
                    bundle_id=base_bundle_id,
                    apis=all_apis,
                    tuple_order_map=base_job.tuple_order_map,
                    start_date=unified_start_date,
                    end_date=unified_end_date,
                )
                merged_jobs.append(merged_bundle)
        
        return merged_jobs
    
    def _build_jobs_from_ranges(
        self,
        context: Dict[str, Any],
        entity_date_ranges: Dict[str, Tuple[str, str]]
    ) -> List[ApiJobBundle]:
        """
        从 entity_date_ranges 构建 job bundles。
        
        Args:
            context: 执行上下文
            entity_date_ranges: 实体日期范围映射
        
        Returns:
            构建的 job bundles 列表
        """
        # 解析 entity_date_ranges
        stock_term_date_ranges = self._parse_entity_date_ranges(entity_date_ranges)
        
        # 获取配置和实体列表
        config = context.get("config")
        if not isinstance(config, DataSourceConfig):
            return []
        apis_conf = config.get_apis()
        entity_list = self._get_entity_list()
        last_update_map = context.get("_last_update_map", {})
        
        # 获取实体标识字段
        entity_key_field = self._get_entity_key_field(config)
        if not entity_key_field:
            logger.error("⚠️ [kline] 无法确定 entity_key_field，无法构建 jobs")
            return []
        
        # 为每个股票构建包含所有周期 API 的 bundle
        merged_jobs: List[ApiJobBundle] = []
        matched_count = 0
        skipped_count = 0
        
        for entity_info in entity_list:
            entity_id = self._extract_entity_id(entity_info, entity_key_field)
            if not entity_id:
                skipped_count += 1
                continue
            
            stock_id = str(entity_id)
            term_date_ranges = stock_term_date_ranges.get(stock_id)
            if not term_date_ranges:
                skipped_count += 1
                continue
            
            # 过滤需要更新的 API
            filtered_apis_conf = self._filter_apis_by_term_update_needs(
                apis_conf, stock_id, term_date_ranges, last_update_map
            )
            
            if not filtered_apis_conf:
                skipped_count += 1
                continue
            
            # 计算统一的日期范围（用于 bundle）
            default_date_range = self._calculate_unified_date_range(term_date_ranges)
            if not default_date_range:
                skipped_count += 1
                continue
            
            # 构建 bundle
            job_bundle = self._build_job(entity_info, filtered_apis_conf, default_date_range)
            if job_bundle is None:
                logger.warning(f"⚠️ [kline] _build_job 返回 None for stock_id={stock_id}")
                skipped_count += 1
                continue
            
            # 为每个 API job 单独设置其对应的 term 的日期范围
            self._set_term_date_ranges_for_apis(job_bundle.apis, term_date_ranges)
            
            merged_jobs.append(job_bundle)
            matched_count += 1
        
        logger.info(
            f"🔧 [kline] 重新构建完成: "
            f"匹配 {matched_count} 个股票，生成 {len(merged_jobs)} 个 job bundles，跳过 {skipped_count} 个"
        )
        
        return merged_jobs
    
    def _get_entity_key_field(self, config: Optional[DataSourceConfig]) -> Optional[str]:
        """获取实体标识字段名。"""
        if not config:
            return None
        
        group_fields = config.get_group_fields()
        if group_fields:
            return group_fields[0]  # 多字段分组时，第一个字段是主键（如 id）
        return config.get_group_by_key()
    
    def _extract_entity_id(self, entity_info: Any, entity_key_field: str) -> Optional[str]:
        """从 entity_info 中提取实体 ID。"""
        if isinstance(entity_info, dict):
            entity_id = entity_info.get(entity_key_field) or entity_info.get("id")
        else:
            entity_id = str(entity_info) if entity_info is not None else None
        
        return str(entity_id) if entity_id else None
    
    def _calculate_unified_date_range(
        self, 
        term_date_ranges: Dict[str, Tuple[str, str]]
    ) -> Optional[Tuple[str, str]]:
        """计算统一的日期范围（取最早的 start_date 和最晚的 end_date）。"""
        if not term_date_ranges:
            return None
        
        all_starts = [dr[0] for dr in term_date_ranges.values()]
        all_ends = [dr[1] for dr in term_date_ranges.values()]
        
        return (min(all_starts), max(all_ends))
    
    def _set_term_date_ranges_for_apis(
        self,
        apis: List[ApiJob],
        term_date_ranges: Dict[str, Tuple[str, str]]
    ) -> None:
        """为每个 API job 设置其对应的 term 的日期范围。"""
        for api_job in apis:
            api_name = api_job.api_name
            term = self.API_TO_TERM.get(api_name)
            
            if term and term in term_date_ranges:
                term_start_date, term_end_date = term_date_ranges[term]
                
                if api_job.params:
                    api_job.params["start_date"] = term_start_date
                    api_job.params["end_date"] = term_end_date
                else:
                    api_job.params = {
                        "start_date": term_start_date,
                        "end_date": term_end_date
                    }
    
    def on_after_single_api_job_bundle_complete(
        self, 
        context: Dict[str, Any], 
        job_bundle: ApiJobBundle, 
        fetched_data: Dict[str, Any]
    ):
        """执行单个 api job bundle 后的钩子：处理并保存 K 线数据。"""
        stock_id = self._extract_stock_id_from_bundle(job_bundle.bundle_id)
        if not stock_id:
            return fetched_data
        
        config = context["config"]
        data_manager = context["data_manager"]
        
        # 遍历 bundle 中的所有 API jobs（每个周期一个）
        for api_job in job_bundle.apis:
            records = self._process_single_api_job(
                api_job, stock_id, fetched_data, config
            )
            if records:
                self._save_kline_records(records, stock_id, context, data_manager)
        
        return fetched_data
    
    def _process_single_api_job(
        self,
        api_job: ApiJob,
        stock_id: str,
        fetched_data: Dict[str, Any],
        config: DataSourceConfig
    ) -> List[Dict[str, Any]]:
        """
        处理单个 API job 的数据：提取、映射、标准化。
        
        Args:
            api_job: API job 实例
            stock_id: 股票 ID
            fetched_data: 抓取的数据
            config: 配置对象
        
        Returns:
            处理后的记录列表，如果处理失败则返回空列表
        """
        api_name = api_job.api_name
        
        # 根据 API 名称确定 term
        term = self.API_TO_TERM.get(api_name)
        if not term:
            logger.warning(f"未知的 API 名称: {api_name}，跳过处理")
            return []
        
        # 获取 job_id（用于从 fetched_data 中提取数据）
        job_id = api_job.job_id or api_job.api_name
        
        # 从 fetched_data 中获取数据
        kline_result = fetched_data.get(job_id)
        if kline_result is None:
            return []
        
        # 转换为 DataFrame
        kline_df = pd.DataFrame(kline_result) if not isinstance(kline_result, pd.DataFrame) else kline_result
        if kline_df.empty:
            return []
        
        # 获取字段映射配置
        api_config = config.get_apis()[api_name]
        result_mapping = api_config.result_mapping
        
        # 转换为记录列表并应用字段映射
        from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
        raw_records = kline_df.to_dict("records")
        mapped_records = DataSourceHandlerHelper._apply_field_mapping(raw_records, result_mapping)
        
        # 添加必需字段（id 和 term）
        for record in mapped_records:
            record["id"] = stock_id
            record["term"] = term
        
        # 清理 NaN 值
        records = self.clean_nan_in_records(mapped_records, default=None)
        
        return records
    
    def _save_kline_records(
        self,
        records: List[Dict[str, Any]],
        stock_id: str,
        context: Dict[str, Any],
        data_manager: Any
    ) -> None:
        """保存 K 线记录到数据库。"""
        term = records[0].get("term", "unknown")
        term_name = self.TERM_TO_NAME.get(term, term)
        
        if context.get("is_dry_run"):
            logger.info(f"🔍 [DRY RUN] 股票 {stock_id} {term_name} K 线数据: {len(records)} 条记录（未实际保存）")
        else:
            data_manager.stock.kline.save(records)
    
    def _extract_stock_id_from_bundle(self, bundle_id: str) -> Optional[str]:
        """从 bundle_id 中提取股票 ID（格式：{data_source_key}_batch_{stock_id}）"""
        if "_batch_" not in bundle_id:
            return None
        parts = bundle_id.split("_batch_")
        return parts[1] if len(parts) >= 2 else None
