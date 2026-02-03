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
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.api_job import ApiJob
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
        """
        构建 job payload：使用固定的 "id" 字段提取实体 ID 并注入到每个 API job 的 params 中。
        
        这样就不需要猜测字段名，格式也确定了。
        """
        if not entity_info:
            return None
        
        # 使用固定的 "id" 字段提取实体 ID
        if isinstance(entity_info, dict):
            entity_id = entity_info.get("id")
        else:
            entity_id = str(entity_info) if entity_info is not None else None
        
        if not entity_id:
            return None
        
        # 为每个 API job 注入实体参数
        for job in apis:
            params = job.params or {}
            api_params = job.api_params or {}
            
            # 使用 API 配置中的 entity_param 字段（必须配置）
            api_param_name = api_params.get("entity_param")
            if not api_param_name:
                logger.warning(
                    f"API {job.api_name} 未配置 entity_param，无法注入实体参数。"
                    f"请在 config.apis.{job.api_name} 中添加 entity_param 配置。"
                )
                continue
            
            # 注入实体参数
            params[api_param_name] = str(entity_id)
            job.params = params
        
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
        # 如果已经有 jobs，说明框架已经处理了（可能是单字段分组的情况）
        # 我们需要检查是否需要合并同一股票的多个周期 jobs
        if jobs:
            # 按股票 ID 分组 jobs
            stock_jobs: Dict[str, List[ApiJobBundle]] = {}
            
            for job in jobs:
                stock_id = self._extract_stock_id_from_bundle(job.bundle_id)
                if not stock_id:
                    continue
                
                if stock_id not in stock_jobs:
                    stock_jobs[stock_id] = []
                stock_jobs[stock_id].append(job)
            
            # 如果每个股票只有一个 job，说明已经合并了，直接返回
            if all(len(job_list) == 1 for job_list in stock_jobs.values()):
                return jobs
            
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
        
        # 如果没有 jobs，说明框架的 _build_jobs 因为多字段分组无法匹配复合 key
        # 我们需要从 entity_date_ranges 中重新构建 jobs
        if not entity_date_ranges:
            logger.warning("⚠️ [kline] entity_date_ranges 为空，无法构建 jobs")
            return jobs
        
        
        # 从 entity_date_ranges 中提取每个股票的每个 term 的日期范围
        # entity_date_ranges 的 key 格式："{stock_id}::{term}"
        # 保留每个 term 的独立日期范围，不要合并
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
        
        
        # 获取配置和实体列表
        config = context.get("config")
        apis_conf = config.get_apis() if config and hasattr(config, "get_apis") else {}
        entity_list = self._get_entity_list()
        
        # 获取实体标识字段：多字段分组时使用第一个字段，单字段分组时使用 key
        entity_key_field = None
        if config:
            group_fields = config.get_group_fields() if hasattr(config, "get_group_fields") else []
            if group_fields and len(group_fields) > 0:
                entity_key_field = group_fields[0]  # 多字段分组时，第一个字段是主键（如 id）
            else:
                entity_key_field = config.get_group_by_key()  # 单字段分组
        
        if not entity_key_field:
            logger.error("⚠️ [kline] 无法确定 entity_key_field，无法构建 jobs")
            return jobs
        
        
        # 为每个股票构建包含所有周期 API 的 bundle
        merged_jobs: List[ApiJobBundle] = []
        matched_count = 0
        skipped_count = 0
        
        for entity_info in entity_list:
            # 提取实体 ID：使用固定的 "id" 字段（与 on_build_job_payload 保持一致）
            if isinstance(entity_info, dict):
                entity_id = entity_info.get("id")
            else:
                entity_id = str(entity_info) if entity_info is not None else None
            
            if not entity_id:
                skipped_count += 1
                continue
            
            stock_id = str(entity_id)
            term_date_ranges = stock_term_date_ranges.get(stock_id)
            if not term_date_ranges:
                skipped_count += 1
                continue
            
            matched_count += 1
            
            # 只创建需要更新的 term 对应的 API jobs，避免创建不需要更新的 job 占用 API 调用窗口
            # 参考 master branch 的做法：检查时间间隔是否 >= 1 个完整周期
            # 1. 先过滤 apis_conf，只保留需要更新的 term 对应的 API
            filtered_apis_conf = {}
            
            # 获取 last_update_map（用于检查时间间隔）
            last_update_map = context.get("_last_update_map", {})
            
            for api_name, api_config in apis_conf.items():
                term = self.API_TO_TERM.get(api_name)
                if term and term in term_date_ranges:
                    # 检查日期范围是否有效（start_date < end_date）
                    term_start_date, term_end_date = term_date_ranges[term]
                    if not DateUtils.is_before(term_start_date, term_end_date):
                        # 日期范围无效，跳过这个 API
                        continue
                    
                    # 参考 master branch：检查时间间隔是否 >= 1 个完整周期
                    composite_key = f"{stock_id}::{term}"
                    last_update = last_update_map.get(composite_key)
                    
                    if last_update:
                        # 已有数据，检查时间间隔是否足够
                        if term == "weekly":
                            # 周线：只有当时间间隔 >= 1 周时才更新
                            # 使用 diff_days 计算天数差，然后除以 7
                            days_diff = DateUtils.diff_days(last_update, term_end_date)
                            time_gap_weeks = days_diff // 7
                            if time_gap_weeks < 1:
                                continue
                        elif term == "monthly":
                            # 月线：只有当时间间隔 >= 1 个月时才更新
                            # 使用更准确的月份计算方法（参考 master branch）
                            from datetime import datetime
                            latest_dt = datetime.strptime(last_update, "%Y%m%d")
                            end_dt = datetime.strptime(term_end_date, "%Y%m%d")
                            year1, month1 = latest_dt.year, latest_dt.month
                            year2, month2 = end_dt.year, end_dt.month
                            month_diff = (year2 - year1) * 12 + (month2 - month1)
                            # 如果天数不足，减一个月
                            if end_dt.day < latest_dt.day:
                                month_diff -= 1
                            if month_diff < 1:
                                continue
                    
                    # 时间间隔足够，保留这个 API
                    filtered_apis_conf[api_name] = api_config
                else:
                    # 找不到对应的 term，说明该 term 在 compute_entity_date_ranges 中被跳过了
                    # 跳过这个 API，不创建 job
                    pass
            
            # 如果所有 API 都被过滤掉了，跳过这个 bundle
            if not filtered_apis_conf:
                skipped_count += 1
                continue
            
            # 获取默认日期范围（用于 bundle 的 start_date 和 end_date）
            # 如果有多个 term，取最早的 start_date 和最晚的 end_date
            default_date_range = None
            if term_date_ranges:
                all_starts = [dr[0] for dr in term_date_ranges.values()]
                all_ends = [dr[1] for dr in term_date_ranges.values()]
                default_date_range = (min(all_starts), max(all_ends))
            
            if not default_date_range:
                skipped_count += 1
                continue
            
            # 构建 bundle（只包含需要更新的 API）
            job_bundle = self._build_job(entity_info, filtered_apis_conf, default_date_range)
            if job_bundle is None:
                logger.warning(f"⚠️ [kline] _build_job 返回 None for stock_id={stock_id}")
                skipped_count += 1
                continue
            
            # 为每个 API job 单独设置其对应的 term 的日期范围
            for api_job in job_bundle.apis:
                api_name = api_job.api_name
                term = self.API_TO_TERM.get(api_name)
                
                if term and term in term_date_ranges:
                    # 找到对应的 term 日期范围，更新 API job 的 params
                    term_start_date, term_end_date = term_date_ranges[term]
                    
                    # 更新 API job 的日期范围参数
                    if api_job.params:
                        api_job.params["start_date"] = term_start_date
                        api_job.params["end_date"] = term_end_date
                    else:
                        api_job.params = {
                            "start_date": term_start_date,
                            "end_date": term_end_date
                        }
            
            
            merged_jobs.append(job_bundle)
        
        logger.info(f"🔧 [kline] 重新构建完成: {len(merged_jobs)} 个 job bundles")
        
        return merged_jobs
    
    def normalize_data(self, context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        覆盖标准化方法：收集所有保存的数据，返回给框架以便更新 last_update。
        
        我们在 on_after_single_api_job_bundle_complete 中已经处理并保存了数据，
        但需要将保存的数据返回给框架，以便框架的 _system_save 能够更新 last_update。
        """
        # 从 context 中获取已保存的数据（由 on_after_single_api_job_bundle_complete 收集）
        all_saved_records = context.get("_kline_saved_records", [])
        
        
        # 返回保存的数据，让框架的 _system_save 能够更新 last_update
        return {"data": all_saved_records}
    
    def on_after_single_api_job_bundle_complete(
        self, 
        context: Dict[str, Any], 
        job_bundle: ApiJobBundle, 
        fetched_data: Dict[str, Any]
    ):
        """
        执行单个 api job bundle 后的钩子：处理并保存 K 线数据。
        
        一个 bundle 包含一个股票的所有周期 API（daily/weekly/monthly），
        我们需要遍历所有 API jobs，分别处理每个周期的数据。
        
        同时收集所有保存的记录，存入 context["_kline_saved_records"]，供 normalize_data 返回给框架。
        """
        if not job_bundle.apis:
            return fetched_data
        
        # 初始化保存记录列表（如果不存在）
        if "_kline_saved_records" not in context:
            context["_kline_saved_records"] = []
        
        # 提取股票 ID（从 bundle_id）
        stock_id = self._extract_stock_id_from_bundle(job_bundle.bundle_id)
        if not stock_id:
            logger.warning(f"⚠️ [kline] 无法从 bundle_id 提取股票 ID: {job_bundle.bundle_id}")
            return fetched_data
        
        # 获取配置和 DataManager
        config = context.get("config")
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.error(f"❌ [kline] DataManager 未初始化，无法保存 K 线数据")
            return fetched_data
        
        from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
        
        # 遍历 bundle 中的所有 API jobs（每个周期一个）
        for api_job in job_bundle.apis:
            api_name = api_job.api_name
            
            # 根据 API 名称确定 term
            term = self.API_TO_TERM.get(api_name)
            if not term:
                logger.warning(f"未知的 API 名称: {api_name}，跳过处理")
                continue
            
            term_name = self.TERM_TO_NAME.get(term, term)
            
            # 获取 job_id（用于从 fetched_data 中提取数据）
            job_id = api_job.job_id or api_job.api_name
            
            # 从 fetched_data 中获取数据
            kline_result = fetched_data.get(job_id)
            if kline_result is None:
                continue
            
            # 转换为 DataFrame
            kline_df = pd.DataFrame(kline_result) if not isinstance(kline_result, pd.DataFrame) else kline_result
            if kline_df.empty:
                continue
            
            # 获取字段映射配置
            apis_conf = config.get_apis() if config and hasattr(config, "get_apis") else {}
            api_config = apis_conf.get(api_name, {})
            field_mapping = api_config.get("field_mapping", {})
            
            # 转换为记录列表
            raw_records = kline_df.to_dict("records")
            
            # 应用字段映射（使用框架的辅助方法）
            mapped_records = DataSourceHandlerHelper._apply_field_mapping(raw_records, field_mapping)
            
            # 添加必需字段（id 和 term）
            for record in mapped_records:
                record["id"] = stock_id
                record["term"] = term
            
            records = mapped_records
            
            # 清理 NaN 值
            records = self.clean_nan_in_records(records, default=None)
            
            if not records:
                continue
            
            # 保存数据（检查是否为 dry run 模式）
            is_dry_run = context.get("is_dry_run", False)
            
            if is_dry_run:
                # Dry run 模式：跳过保存，但仍收集记录供 normalize_data 返回
                context["_kline_saved_records"].extend(records)
            else:
                try:
                    count = data_manager.stock.kline.save(records)
                    # 收集已保存的记录，供 normalize_data 返回给框架
                    context["_kline_saved_records"].extend(records)
                except Exception as e:
                    logger.error(f"❌ 保存股票 {stock_id} {term_name} K 线数据失败: {e}", exc_info=True)
        
        return fetched_data
    
    def _extract_stock_id_from_bundle(self, bundle_id: str) -> Optional[str]:
        """
        从 bundle_id 中提取股票 ID（格式：{data_source_key}_batch_{stock_id}）
        
        例如：kline_batch_000001.SZ -> 000001.SZ
        """
        if "_batch_" not in bundle_id:
            logger.warning(f"无法从 bundle_id 中提取股票 ID: {bundle_id}")
            return None
        
        parts = bundle_id.split("_batch_")
        if len(parts) < 2:
            logger.warning(f"bundle_id 格式不正确: {bundle_id}")
            return None
        
        return parts[1]
