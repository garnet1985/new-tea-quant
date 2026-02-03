"""
企业财务数据 Handler

从 Tushare 获取企业财务指标数据（季度）
"""
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.utils.date.date_utils import DateUtils


class CorporateFinanceHandler(BaseHandler):
    """
    企业财务数据 Handler
    
    从 Tushare 获取企业财务指标数据（季度）。
    
    特点：
    - 季度数据（YYYYQ[1-4] 格式）
    - 滚动窗口更新（rolling）：由框架自动处理
    - 需要按股票逐个获取（每个股票一个 ApiJob）
    - 支持轮转批次（每次只处理一部分股票）：由框架自动处理
    - 支持滚动窗口（每次刷新最近 N 个季度）：由框架自动处理
    
    配置（在 config.py 中）：
    - save_mode: "batch" (批量保存：累计 save_batch_size 个 bundle 后保存)
    - save_batch_size: 20 (每20个bundle保存一次)
    - renew.type: "rolling" (滚动窗口模式，框架自动处理)
    - renew.rolling.unit: "quarter" (滚动单位)
    - renew.rolling.length: 3 (滚动窗口长度，3个季度)
    - renew.batch_selection.num_batches: 8 (轮转批次数，框架自动处理)
    - renew.batch_selection.cache_key: "corporate_finance_batch_offset" (批次 offset 缓存 key)
    - apis: {...} (包含 finance_data API 配置)
    
    实现说明：
    - 框架自动处理批次选择：从 context 取出 list，从 db 找 offset，选择批次，保存 offset
    - 框架自动处理滚动窗口：基于 last_update 和 rolling 配置计算日期范围
    - handler 只需要处理业务逻辑：数据标准化（end_date -> quarter）和数据保存
    """

    CACHE_KEY = "corporate_finance_batch_offset"
    BATCH_AMOUNT = 10
    MIN_BATCH_SIZE = 1
    MAX_BATCH_SIZE = 450
    
    def __init__(
        self,
        data_source_key: str,
        schema,
        config,
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
        """构建 job payload：手动注入 ts_code 参数到每个 API job 的 params 中。"""
        entity_id = entity_info.get("id") if isinstance(entity_info, dict) else str(entity_info)
        if not entity_id:
            return None
        
        # 为每个 API job 手动注入 ts_code 参数
        for job in apis:
            job.params = job.params or {}
            job.params["ts_code"] = str(entity_id)
        
        return str(entity_id)
    
    def on_prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """预处理阶段的上下文准备钩子：通过切片 stock_list 实现批次选择。"""
        context = super().on_prepare_context(context)
        
        all_stocks = context["dependencies"]["stock_list"]
        if not all_stocks:
            return context
        
        # 从 db_cache 读取批次 offset
        data_manager = context["data_manager"]
        batch_offset = 0
        try:
            cache_row = data_manager.db_cache.get(self.CACHE_KEY)
            if cache_row and cache_row.get('value'):
                batch_offset = int(cache_row['value'])
        except Exception:
            pass
        
        # 计算批次大小并做环形切片（分成 8 个批次）
        L = len(all_stocks)
        batch_size = max(self.MIN_BATCH_SIZE, min(self.MAX_BATCH_SIZE, L // self.BATCH_AMOUNT))
        indices = [(batch_offset + i) % L for i in range(batch_size)]
        selected_stocks = [all_stocks[i] for i in indices]
        new_offset = (batch_offset + batch_size) % L
        
        # 注入到 context 并保存 offset
        context["stock_list"] = selected_stocks
        try:
            data_manager.db_cache.set(self.CACHE_KEY, str(new_offset))
        except Exception:
            pass
        
        logger.info(f"✅ 批次选择完成：从 {len(all_stocks)} 只股票中选择 {len(selected_stocks)} 只")
        return context
    
    
    def on_after_single_api_job_bundle_complete(
        self, 
        context: Dict[str, Any], 
        job_bundle: Any, 
        fetched_data: Dict[str, Any]
    ):
        """单个 api job bundle 完成后的钩子：标准化并保存该股票的企业财务数据。"""
        stock_id = job_bundle.bundle_id.replace("corporate_finance_batch_", "")
        api_job = job_bundle.apis[0]
        job_id = api_job.job_id or api_job.api_name
        result = fetched_data.get(job_id)
        
        if result is None:
            return fetched_data
        
        # 标准化数据
        normalized = self._normalize_single_stock_data(context, result, stock_id)
        if not normalized.get("data"):
            return fetched_data
        
        # 使用框架的 _system_save 保存数据
        if not context.get("is_dry_run"):
            self._system_save(normalized)
            logger.info(f"✅ [单股票保存] {stock_id}: {len(normalized['data'])} 条企业财务记录")
        
        return fetched_data
    
    def _normalize_single_stock_data(
        self, 
        context: Dict[str, Any], 
        result: Any,
        stock_id: str
    ) -> Dict[str, Any]:
        """标准化单个股票的数据：字段映射 + end_date -> quarter 转换。"""
        records = DataSourceHandlerHelper.result_to_records(result)
        if not records:
            return {"data": []}
        
        records = self.clean_nan_in_records(records, default=None)
        field_mapping = context["config"].get_apis()["finance_data"]["field_mapping"]
        mapped_records = DataSourceHandlerHelper._apply_field_mapping(records, field_mapping)
        
        # 处理特殊转换：end_date -> quarter, 添加 id
        # 问题：API 可能返回重复记录，包括：
        # 1. 同一个季度的多个不同 end_date（如 20230315 和 20230331），都转换为同一个 quarter
        # 2. 完全相同的 end_date 的多条记录（API 数据源本身有重复）
        # 解决：按 quarter 去重，保留 end_date 最大的记录（通常是最新的）
        # 如果 end_date 相同，保留第一条（通常 API 返回的重复记录内容也相同）
        quarter_records = {}  # {quarter: record} 用于去重，保留 end_date 最大的
        for record in mapped_records:
            end_date_raw = record.get('end_date', '')
            end_date = str(end_date_raw).replace('-', '')
            
            # 检查日期格式
            if len(end_date) != 8:
                logger.debug(f"⚠️ {stock_id}: end_date 格式异常: {end_date_raw} -> {end_date}")
                continue
            
            quarter = DateUtils.date_to_quarter(end_date)
            if not quarter:
                logger.debug(f"⚠️ {stock_id}: 无法转换 end_date 到 quarter: {end_date}")
                continue
            
            # 如果该 quarter 已存在，比较 end_date，保留较大的（最新的）
            if quarter in quarter_records:
                existing_end_date = str(quarter_records[quarter].get('end_date', '')).replace('-', '')
                if end_date > existing_end_date:
                    logger.debug(f"🔄 {stock_id}: quarter {quarter} 有重复，保留更新的 end_date: {end_date_raw} (替换 {existing_end_date})")
                    quarter_records[quarter] = record
            else:
                quarter_records[quarter] = record
        
        # 转换为最终格式
        formatted = []
        for quarter, record in quarter_records.items():
            record["id"] = stock_id
            record["quarter"] = quarter
            record.pop("end_date", None)
            formatted.append(record)
        
        return {"data": formatted}
    
