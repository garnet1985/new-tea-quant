"""
复权因子事件 Handler（简化版 - 使用框架钩子）

特点：
- CSV缓存：空表时从CSV快速恢复
- 批量筛选：框架自动处理 renew_if_over_days
- 多线程支持：框架自动处理
- 季度CSV导出：定期备份数据
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import os

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from userspace.data_source.handlers.adj_factor_event.helper import AdjFactorEventHandlerHelper as helper
from core.infra.project_context import ConfigManager


class AdjFactorEventHandler(BaseHandler):
    """
    复权因子事件 Handler（简化版）
    
    使用框架的标准钩子：
    - on_prepare_context: CSV 导入检查
    - on_build_job_payload: 注入股票代码和日期参数
    - on_after_single_api_job_bundle_complete: 处理每个股票的数据
    - on_after_normalize: CSV 导出
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
        self._completed_stocks = 0
        self._total_stocks = 0
    
    def on_prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """预处理阶段的上下文准备钩子：CSV 导入检查（如果 model 支持）。"""
        context = super().on_prepare_context(context)
        
        data_manager = context["data_manager"]
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        
        # 记录本轮执行对应的最新完成交易日，用于后续季度 CSV 命名
        self._latest_completed_trading_date = latest_completed_trading_date
        
        adj_factor_event_model = data_manager.stock.kline._adj_factor_event
        
        # CSV 导入检查（如果 model 支持 CSV 功能）
        context["should_generate_csv"] = False
        
        # 检查 model 是否支持表空检查
        is_table_empty = False
        if hasattr(adj_factor_event_model, 'is_table_empty'):
            is_table_empty = adj_factor_event_model.is_table_empty()
        else:
            # 如果没有 is_table_empty 方法，尝试使用 count 方法
            try:
                count = adj_factor_event_model.count()
                is_table_empty = count == 0
            except Exception:
                # 如果都不可用，假设表不为空，跳过 CSV 导入
                return context
        
        if is_table_empty:
            # 表为空：尝试从 CSV 恢复（如果支持）
            if hasattr(adj_factor_event_model, 'get_latest_csv_file') and hasattr(adj_factor_event_model, 'import_from_csv'):
                if self._is_csv_exist_and_valid(adj_factor_event_model):
                    imported_count = adj_factor_event_model.import_from_csv()
                    if imported_count > 0:
                        logger.info(f"✅ 从CSV导入 {imported_count} 条记录，表已恢复")
                    else:
                        logger.warning("CSV导入失败或无数据")
                else:
                    logger.info("表为空且无有效CSV，将进行首次构建")
            else:
                logger.info("表为空，将进行首次构建（CSV功能未启用）")
        else:
            # 表不为空：检查是否需要生成新的 CSV（如果支持）
            if hasattr(adj_factor_event_model, 'get_latest_csv_file') and hasattr(adj_factor_event_model, 'get_current_quarter_csv_name'):
                if self._is_csv_expired(adj_factor_event_model, base_date=latest_completed_trading_date) or not self._is_csv_exist_and_valid(adj_factor_event_model):
                    context["should_generate_csv"] = True
                    logger.info("CSV已过期或不存在，将在更新后生成新CSV")
        
        return context
    
    def on_build_job_payload(
        self,
        entity_info: Any,
        apis: List[ApiJob],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """构建 job payload：注入股票代码和日期参数到每个 API job。"""
        entity_id = entity_info.get("id") if isinstance(entity_info, dict) else str(entity_info)
        if not entity_id:
            return None
        
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        default_start_date = ConfigManager.get_default_start_date()
        
        # 为每个 API job 注入参数
        for job in apis:
            job.params = job.params or {}
            
            # 注入股票代码（根据 API 类型使用不同的参数名）
            if job.api_name == "qfq_kline":
                # EastMoney API 使用 secid
                eastmoney_secid = helper.convert_to_eastmoney_secid(entity_id)
                job.params["secid"] = eastmoney_secid
            else:
                # Tushare API 使用 ts_code
                job.params["ts_code"] = str(entity_id)
            
            # 注入日期参数
            job.params["start_date"] = default_start_date
            job.params["end_date"] = latest_completed_trading_date
        
        return str(entity_id)
    
    def on_after_single_api_job_bundle_complete(
        self,
        context: Dict[str, Any],
        job_bundle: ApiJobBundle,
        fetched_data: Dict[str, Any]
    ):
        """单个 api job bundle 完成后的钩子：处理该股票的复权因子事件数据。"""
        # 从 bundle_id 提取股票代码（格式：adj_factor_event_batch_{stock_id}）
        stock_id = job_bundle.bundle_id.replace("adj_factor_event_batch_", "")
        
        # 获取该股票的 3 个 API 结果（使用 api_name 作为 key，因为 job_id 默认等于 api_name）
        adj_factor_result = None
        daily_kline_result = None
        qfq_kline_result = None
        
        for api_job in job_bundle.apis:
            # job_id 默认等于 api_name（如果没有显式设置）
            job_id = api_job.job_id or api_job.api_name
            result = fetched_data.get(job_id)
            
            if api_job.api_name == "adj_factor":
                adj_factor_result = result
            elif api_job.api_name == "daily_kline":
                daily_kline_result = result
            elif api_job.api_name == "qfq_kline":
                qfq_kline_result = result
        
        # 调试：如果 qfq_kline_result 不是 dict，记录详细信息
        if qfq_kline_result is not None and not isinstance(qfq_kline_result, dict):
            logger.debug(f"{stock_id}: qfq_kline_result 类型异常: {type(qfq_kline_result)}, 值: {str(qfq_kline_result)[:200]}")
            logger.debug(f"{stock_id}: fetched_data keys: {list(fetched_data.keys())}")
            logger.debug(f"{stock_id}: job_bundle.apis: {[api.api_name for api in job_bundle.apis]}")
        
        # 验证必需的数据
        import pandas as pd
        if adj_factor_result is None or (isinstance(adj_factor_result, pd.DataFrame) and adj_factor_result.empty):
            logger.debug(f"{stock_id}: 复权因子数据为空，跳过")
            return fetched_data
        
        if daily_kline_result is None or (isinstance(daily_kline_result, pd.DataFrame) and daily_kline_result.empty):
            logger.debug(f"{stock_id}: 日线数据为空，跳过")
            return fetched_data
        
        # 解析 EastMoney 全量数据，构建日期 -> QFQ 价格的映射
        # 注意：qfq_kline_result 可能为 None 或非 dict（API 失败或返回格式异常）
        # parse_eastmoney_qfq_price_map 会处理这种情况，返回空字典
        if qfq_kline_result is not None and not isinstance(qfq_kline_result, dict):
            logger.debug(f"{stock_id}: 东方财富 API 返回的数据格式异常（类型: {type(qfq_kline_result)}），将使用空映射")
        
        eastmoney_qfq_map = helper.parse_eastmoney_qfq_price_map(qfq_kline_result)
        
        # 关键：EastMoney 失败时（如 RemoteDisconnected）eastmoney_qfq_map 为空，
        # 若仍保存会导致 qfq_diff=0 覆盖 DB 中已有的正确复权数据，必须跳过
        if not eastmoney_qfq_map:
            logger.warning(
                f"{stock_id}: 东方财富前复权数据为空（API 失败或返回异常），跳过保存，保留 DB 原有数据"
            )
            return fetched_data
        
        # 处理日线数据，构建日期 -> 原始收盘价的映射
        raw_price_map = helper.build_raw_price_map(daily_kline_result)
        
        # 获取第一根日线日期
        first_kline_ymd = None
        if eastmoney_qfq_map:
            first_kline_ymd = min(eastmoney_qfq_map.keys())
        elif isinstance(daily_kline_result, pd.DataFrame) and 'trade_date' in daily_kline_result.columns:
            first_kline_date = daily_kline_result['trade_date'].min()
            first_kline_ymd = helper.normalize_date_to_yyyymmdd(str(first_kline_date))
        
        if not first_kline_ymd:
            logger.debug(f"{stock_id}: 没有第一根K线数据，跳过复权因子保存")
            return fetched_data
        
        # 构建复权因子事件列表
        events_to_save = helper.build_adj_factor_events(
            stock_id=stock_id,
            adj_factor_df=adj_factor_result,
            raw_price_map=raw_price_map,
            eastmoney_qfq_map=eastmoney_qfq_map,
            first_kline_ymd=first_kline_ymd
        )
        
        # 保存该股票的复权事件（全量替换：先删除再保存）
        if events_to_save and not context.get("is_dry_run"):
            data_manager = context["data_manager"]
            data_manager.stock.kline.delete_adj_factor_events(stock_id)
            count = data_manager.stock.kline.save_adj_factor_events(events_to_save)
            logger.info(f"✅ [全量替换] {stock_id}: 保存了 {len(events_to_save)} 个复权事件（实际保存 {count} 条）")
            self._completed_stocks += 1
        
        return fetched_data
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化后处理：季度CSV导出（如果 model 支持）。"""
        data_manager = context.get("data_manager")
        if not data_manager:
            return normalized_data
        
        # 检查是否需要导出CSV
        if not context.get("should_generate_csv"):
            return normalized_data
        
        adj_factor_event_model = data_manager.stock.kline._adj_factor_event
        
        # 检查 model 是否支持 CSV 导出功能
        if not (hasattr(adj_factor_event_model, 'get_current_quarter_csv_name') and 
                hasattr(adj_factor_event_model, 'csv_dir') and 
                hasattr(adj_factor_event_model, 'export_to_csv')):
            logger.debug("CSV导出功能未启用（model 不支持）")
            return normalized_data
        
        base_date = getattr(self, "_latest_completed_trading_date", None)
        current_csv_name = adj_factor_event_model.get_current_quarter_csv_name(base_date=base_date)
        current_csv_path = os.path.join(adj_factor_event_model.csv_dir, current_csv_name)
        
        if not os.path.exists(current_csv_path):
            logger.info("📋 导出季度CSV...")
            exported_count = adj_factor_event_model.export_to_csv(file_path=current_csv_path)
            if exported_count > 0:
                logger.info(f"✅ 导出季度CSV完成: {exported_count} 条记录 -> {current_csv_name}")
            else:
                logger.warning("导出季度CSV失败")
        else:
            logger.debug(f"当前季度CSV已存在: {current_csv_name}")
        
        return normalized_data
    
    def _is_csv_exist_and_valid(self, adj_factor_event_model) -> bool:
        """检查CSV文件是否存在且有效（如果 model 支持）"""
        if not hasattr(adj_factor_event_model, 'get_latest_csv_file'):
            return False
        
        csv_file = adj_factor_event_model.get_latest_csv_file()
        if not csv_file or not os.path.exists(csv_file):
            return False
        
        try:
            import pandas as pd
            df = pd.read_csv(csv_file, nrows=1)
            required_columns = ['id', 'event_date', 'factor', 'qfq_diff']
            return all(col in df.columns for col in required_columns)
        except Exception:
            return False
    
    def _is_csv_expired(self, adj_factor_event_model, base_date: str = None) -> bool:
        """检查CSV文件是否过期（超过一个季度）（如果 model 支持）"""
        if not (hasattr(adj_factor_event_model, 'get_latest_csv_file') and 
                hasattr(adj_factor_event_model, 'get_current_quarter_csv_name')):
            return True
        
        csv_file = adj_factor_event_model.get_latest_csv_file()
        if not csv_file:
            return True
        
        current_csv_name = adj_factor_event_model.get_current_quarter_csv_name(base_date=base_date)
        csv_name = os.path.basename(csv_file)
        return csv_name != current_csv_name
