"""
企业财务数据 Handler

从 Tushare 获取企业财务指标数据（季度）
"""
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Union
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.infra.project_context import ConfigManager
from core.utils.date.date_utils import DateUtils


class CorporateFinanceHandler(BaseHandler):
    """
    企业财务数据 Handler
    
    从 Tushare 获取企业财务指标数据（季度）。
    
    特点：
    - 季度数据（YYYYQ[1-4] 格式）
    - 增量更新（incremental）
    - 需要按股票逐个获取（每个股票一个 ApiJob）
    - 需要计算日期范围（基于数据库最新记录）
    - 支持轮转批次（每次只处理一部分股票）
    - 支持滚动窗口（每次刷新最近 N 个季度）
    
    配置（在 config.json 中）：
    - renew_mode: "incremental"
    - date_format: "quarter"
    - rolling_quarters: 3 (滚动窗口季度数)
    - renew_rolling_batch: 8 (轮转批次数)
    - apis: {...} (包含 finance_data API 配置)
    """
    
    def __init__(self, data_source_key: str, schema, config, providers: Dict[str, BaseProvider]):
        super().__init__(data_source_key, schema, config, providers)
        
        # 从 config 获取参数
        if hasattr(config, "get"):
            self.rolling_quarters = config.get("rolling_quarters", 3)
            self.renew_rolling_batch = config.get("renew_rolling_batch", 8)
        else:
            self.rolling_quarters = getattr(config, "rolling_quarters", 3) if hasattr(config, "rolling_quarters") else 3
            self.renew_rolling_batch = getattr(config, "renew_rolling_batch", 8) if hasattr(config, "renew_rolling_batch") else 8
    
    def on_calculate_date_range(self, context: Dict[str, Any], apis: List[ApiJob]) -> Optional[Union[Tuple[str, str], Dict[str, Tuple[str, str]]]]:
        """
        自定义日期范围计算钩子：实现企业财务数据的特殊逻辑
        
        逻辑：
        1. 获取股票列表
        2. 查询数据库获取每个股票的最新季度
        3. 计算每个股票的起始日期（考虑滚动窗口）
        4. 返回 per stock 日期范围字典
        
        Args:
            context: 执行上下文
            apis: ApiJob 列表
            
        Returns:
            Dict[str, Tuple[str, str]]: {stock_id: (start_date, end_date)}
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法计算日期范围")
            return None
        
        # 获取股票列表
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("股票列表为空，无法计算日期范围")
            return None
        
        # 获取最新完成交易日
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date:
            try:
                latest_completed_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
            except Exception as e:
                logger.warning(f"获取最新完成交易日失败: {e}")
                return None
        
        # 构建需要更新的股票列表（包含日期范围）
        target_list = self._build_renewable_stock_list(
            latest_completed_trading_date, 
            stock_list,
            data_manager
        )
        
        if not target_list:
            logger.info("没有需要更新的股票")
            return {}
        
        # 转换为 per stock 日期范围字典
        date_ranges = {}
        for stock in target_list:
            stock_id = stock.get('stock_id')
            start_date = stock.get('start_date')
            end_date = stock.get('end_date')
            if stock_id and start_date and end_date:
                date_ranges[stock_id] = (start_date, end_date)
        
        logger.info(f"✅ 为 {len(date_ranges)} 只股票计算了日期范围")
        return date_ranges
    
    def _build_renewable_stock_list(
        self, 
        latest_completed_trading_date: str, 
        stock_list: List[Dict[str, Any]],
        data_manager
    ) -> List[Dict[str, Any]]:
        """
        构建需要更新的股票列表
        
        Args:
            latest_completed_trading_date: 最新完成交易日（YYYYMMDD格式）
            stock_list: 股票列表
            data_manager: DataManager 实例
            
        Returns:
            List[Dict]: 需要更新的股票列表，每个元素包含：
                - stock_id: 股票代码
                - start_date: 起始日期（YYYYMMDD格式）
                - end_date: 结束日期（YYYYMMDD格式）
        """
        # 计算当前季度，作为本次任务的"有效上界"季度
        max_effective_quarter = DateUtils.get_current_quarter(latest_completed_trading_date)
        
        # 从 DB 中获取所有股票最新的财报季度信息：{stock_id: last_updated_quarter}
        raw_map = data_manager.service.stock.corporate_finance.get_stocks_latest_update_quarter()
        
        # 如果 DB 里完全没有企业财务数据，这是第一次跑
        is_first_run = not raw_map
        
        target_list = []
        end_date = latest_completed_trading_date
        
        # 系统的历史起点季度
        base_quarter = DateUtils.date_to_quarter(ConfigManager.get_default_start_date())
        
        # 工具函数：将季度转为线性索引
        def quarter_to_index(q_str: str) -> int:
            year = int(q_str[:4])
            quarter = int(q_str[5])
            return year * 4 + quarter
        
        max_index = quarter_to_index(max_effective_quarter)
        
        # ========== 轮转批次选择 ==========
        all_stocks = list(stock_list or [])
        if not all_stocks:
            return []
        
        effective_stock_list = all_stocks
        batch_size = len(all_stocks)
        batch_offset = 0
        
        if not is_first_run and self.renew_rolling_batch and len(all_stocks) > 0:
            batch_size = max(1, len(all_stocks) // self.renew_rolling_batch)
            
            try:
                cache_key = 'corporate_finance_batch_offset'
                cache_row = data_manager.db_cache.get(cache_key)
                if cache_row and cache_row.get('value') is not None:
                    try:
                        batch_offset = int(cache_row['value'])
                    except (TypeError, ValueError):
                        batch_offset = 0
                else:
                    batch_offset = 0
            except Exception as e:
                logger.warning(f"读取批次游标失败，将从头开始轮转: {e}")
                batch_offset = 0
            
            # 根据 offset 做环形切片
            L = len(all_stocks)
            indices = [(batch_offset + i) % L for i in range(batch_size)]
            effective_stock_list = [all_stocks[i] for i in indices]
            
            # 预先计算新的 offset
            new_offset = (batch_offset + batch_size) % L
        else:
            new_offset = 0
        
        # 针对本次选中的股票逐一决定起始日期
        for stock in effective_stock_list:
            stock_id = stock.get("id") or stock.get("ts_code")
            if not stock_id:
                continue
            
            # 第一次跑：对所有股票从系统默认起点全量拉取
            if is_first_run:
                start_date = ConfigManager.get_default_start_date()
            else:
                last_q = raw_map.get(stock_id)
                
                if not last_q:
                    # DB 中没有这只股票：视为新股，从默认起点开始全量拉取
                    start_date = ConfigManager.get_default_start_date()
                else:
                    # 下一个应更新的季度
                    next_q = DateUtils.get_next_quarter(last_q)
                    next_index = quarter_to_index(next_q)
                    
                    # 计算"滚动窗口"的最老季度：max_q 往前 ROLLING_QUARTERS-1 个季度
                    window_oldest_index = max_index - (self.rolling_quarters - 1)
                    window_oldest_quarter = base_quarter
                    if quarter_to_index(base_quarter) < window_oldest_index:
                        tmp_q = base_quarter
                        while quarter_to_index(tmp_q) < window_oldest_index:
                            tmp_q = DateUtils.get_next_quarter(tmp_q)
                        window_oldest_quarter = tmp_q
                    
                    # 情况 1：如果 next_q 已经落在或早于窗口起点，说明"追平进度"后，
                    # 只需要滚动刷新最近 ROLLING_QUARTERS 个季度即可。
                    if next_index <= window_oldest_index:
                        start_quarter = window_oldest_quarter
                    else:
                        # 情况 2：这只股票落后超过 ROLLING_QUARTERS 个季度，
                        # 需要从 last_q 对应季度的起点开始回补，一路补到当前有效季度。
                        start_quarter = last_q
                    
                    # 将起始季度转换为日期
                    start_date = DateUtils.get_quarter_start_date(start_quarter)
            
            target_list.append({
                "stock_id": stock_id,
                "start_date": start_date,
                "end_date": end_date,
            })
        
        # 非首次跑时，将新的 batch_offset 写回 system_cache
        if not is_first_run and self.renew_rolling_batch and target_list:
            try:
                cache_key = 'corporate_finance_batch_offset'
                data_manager.db_cache.set(
                    key=cache_key,
                    value=str(new_offset)
                )
            except Exception as e:
                logger.warning(f"写入批次游标失败，不影响本次任务: {e}")
        
        return target_list
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：为每个股票创建 ApiJob 并注入日期范围
        
        由于基类在调用此方法前已经调用了 on_calculate_date_range，但此时 apis 只有一个 base_api，
        无法注入 per stock 日期范围。所以我们需要：
        1. 重新调用 on_calculate_date_range 获取 per stock 日期范围
        2. 为每个股票创建 ApiJob（设置 ts_code）
        3. 手动注入日期范围
        
        Args:
            context: 执行上下文
            apis: 原始 ApiJob 列表（从 config 构建，只有一个 base_api）
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表（每个股票一个 ApiJob，已注入日期范围）
        """
        # 获取股票列表
        stock_list = context.get("stock_list", [])
        if not stock_list:
            return apis
        
        # 获取 per stock 日期范围
        date_ranges = self.on_calculate_date_range(context, apis)
        if not date_ranges or not isinstance(date_ranges, dict):
            logger.warning("无法获取 per stock 日期范围，使用默认逻辑")
            return apis
        
        expanded_apis = []
        base_api = apis[0] if apis else None
        
        if not base_api:
            logger.warning("未找到 base API，无法创建股票 ApiJobs")
            return apis
        
        # 为每个股票创建 ApiJob 并注入日期范围
        for stock_id, (start_date, end_date) in date_ranges.items():
            new_api = ApiJob(
                api_name=base_api.api_name,
                provider_name=base_api.provider_name,
                method=base_api.method,
                params={
                    **base_api.params,
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                api_params=base_api.api_params,
                depends_on=base_api.depends_on,
                rate_limit=base_api.rate_limit,
                job_id=f"{stock_id}_finance",
            )
            expanded_apis.append(new_api)
        
        logger.info(f"✅ 为 {len(expanded_apis)} 只股票生成了企业财务数据获取任务")
        return expanded_apis
    
    def on_after_execute_single_api_job(
        self, 
        context: Dict[str, Any], 
        api_job: ApiJob, 
        fetched_data: Dict[str, Any]
    ):
        """
        单个 ApiJob 执行完成后的钩子：就地保存该股票的企业财务数据
        
        避免在所有股票都跑完之后一次性落库，改为"一个股票一保存"
        
        注意：此处的保存逻辑是按实体（股票）逐个保存，属于执行期保存模式。
        如果未来需要将 save 逻辑完全抽离到上层，可以移除此处的保存调用。
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法保存企业财务数据")
            return
        
        try:
            # 提取该股票的数据
            job_id = api_job.job_id
            result = fetched_data.get(job_id)
            
            if not result:
                logger.debug(f"⚠️ {job_id} 没有数据，跳过保存")
                return
            
            # 标准化该股票的数据
            normalized = self._normalize_single_stock_data(context, result, api_job)
            
            data_list = normalized.get("data", [])
            if not data_list:
                logger.debug(f"⚠️ {job_id} 标准化后没有有效数据，跳过保存")
                return
            
            # 使用 service 保存数据
            saved_count = data_manager.stock.corporate_finance.save_batch(data_list)
            logger.info(f"✅ [单股票保存] {job_id}: 保存 {saved_count} 条企业财务记录")
        except Exception as e:
            logger.error(f"❌ 保存 {api_job.job_id} 企业财务数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _normalize_single_stock_data(
        self, 
        context: Dict[str, Any], 
        result: Any,
        api_job: ApiJob
    ) -> Dict[str, Any]:
        """
        标准化单个股票的数据
        
        Args:
            context: 执行上下文
            result: API 返回的原始数据
            api_job: ApiJob 实例（用于提取 stock_id）
            
        Returns:
            Dict[str, Any]: 标准化后的数据 {"data": [...]}
        """
        formatted = []
        
        # 转换为记录列表
        records = DataSourceHandlerHelper.result_to_records(result)
        if not records:
            return {"data": []}
        
        # 使用统一 helper 清理所有记录中的 NaN 值
        records = self.clean_nan_in_records(records, default=None)
        
        # 从 job_id 提取 stock_id
        job_id = api_job.job_id
        stock_id = job_id.replace("_finance", "")
        
        # 字段映射和数据处理
        for item in records:
            # 将 end_date 转换为 quarter
            end_date = str(item.get('end_date', ''))
            # 确保 end_date 是 YYYYMMDD 格式
            if '-' in end_date:
                end_date = end_date.replace('-', '')
            
            quarter = DateUtils.date_to_quarter(end_date)
            
            if not quarter:
                logger.debug(f"无法将日期 {end_date} 转换为季度，跳过该记录")
                continue
            
            # 辅助函数：安全地将值转换为 float，处理 NaN
            def safe_float(value, default=0.0):
                """安全转换为 float，处理 NaN 和 None"""
                # 使用 BaseHandler 的 clean_nan_in_records 已经清理过，这里只需要类型转换
                if value is None:
                    return default
                try:
                    result = float(value)
                    import math
                    if math.isnan(result):
                        return default
                    return result
                except (TypeError, ValueError):
                    return default
            
            # 字段映射
            mapped = {
                "id": stock_id,
                "quarter": quarter,
                # 盈利能力指标
                "eps": safe_float(item.get('eps')),
                "dt_eps": safe_float(item.get('dt_eps')),
                "roe": safe_float(item.get('roe')),
                "roe_dt": safe_float(item.get('roe_dt')),
                "roa": safe_float(item.get('roa')),
                "netprofit_margin": safe_float(item.get('netprofit_margin')),
                "gross_profit_margin": safe_float(item.get('grossprofit_margin')),  # API字段名差异
                "op_income": safe_float(item.get('op_income')),
                "roic": safe_float(item.get('roic')),
                "ebit": safe_float(item.get('ebit')),
                "ebitda": safe_float(item.get('ebitda')),
                "dtprofit_to_profit": safe_float(item.get('dtprofit_to_profit')),
                "profit_dedt": safe_float(item.get('profit_dedt')),
                # 成长能力指标
                "or_yoy": safe_float(item.get('or_yoy')),
                "netprofit_yoy": safe_float(item.get('netprofit_yoy')),
                "basic_eps_yoy": safe_float(item.get('basic_eps_yoy')),
                "dt_eps_yoy": safe_float(item.get('dt_eps_yoy')),
                "tr_yoy": safe_float(item.get('tr_yoy')),
                # 偿债能力指标
                "netdebt": safe_float(item.get('netdebt')),
                "debt_to_eqt": safe_float(item.get('debt_to_eqt')),
                "debt_to_assets": safe_float(item.get('debt_to_assets')),
                "interestdebt": safe_float(item.get('interestdebt')),
                "assets_to_eqt": safe_float(item.get('assets_to_eqt')),
                "quick_ratio": safe_float(item.get('quick_ratio')),
                "current_ratio": safe_float(item.get('current_ratio')),
                # 运营能力指标
                "ar_turn": safe_float(item.get('ar_turn')),
                # 资产状况指标
                "bps": safe_float(item.get('bps')),
                # 现金流指标
                "ocfps": safe_float(item.get('ocfps')),
                "fcff": safe_float(item.get('fcff')),
                "fcfe": safe_float(item.get('fcfe')),
            }
            
            # 只保留有效的记录（必须有 id 和 quarter）
            if mapped.get('id') and mapped.get('quarter'):
                formatted.append(mapped)
        
        return {
            "data": formatted
        }
    
    def _normalize_data(self, context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据：覆盖基类方法，因为数据已经在 on_after_execute_single_api_job 中保存
        
        这里只返回空数据，避免重复处理
        """
        # 数据已经在 on_after_execute_single_api_job 中按股票逐个保存
        # 这里不需要再次处理，返回空数据即可
        return {"data": []}
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：这里只做日志，不再统一写库
        
        企业财务数据的落库已经在 on_after_execute_single_api_job 中
        按股票粒度完成，避免重复保存
        """
        data_list = normalized_data.get("data") or []
        logger.info(f"✅ 企业财务数据标准化完成（按股票已分别保存），总记录数: {len(data_list)}")
        return normalized_data
