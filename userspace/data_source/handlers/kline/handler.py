"""
K线数据 Handler

从 Tushare 获取股票 K 线数据（日线/周线/月线）
以股票为单位处理，每个股票创建 4 个 API Job：
1. get_daily_kline - 日线价格和成交量数据
2. get_weekly_kline - 周线价格和成交量数据
3. get_monthly_kline - 月线价格和成交量数据
4. get_daily_basic - 基本面指标（PE、PB、换手率、市值等）

说明：
- daily/weekly/monthly API 只返回价格和成交量数据（open, high, low, close, volume, amount）
- daily_basic API 返回基本面指标（PE、PB、换手率、市值等）
- 需要合并 K 线数据和 daily_basic 数据才能得到完整的 K 线数据
- 优势：daily_basic 只调用一次，减少 API 调用次数（从 6N 降到 4N）

保存策略：
- 在 on_after_execute_job_batch_for_single_stock 钩子中，按股票分组保存数据
- 每个股票的所有周期数据获取完成后，立即保存该股票的数据
"""
from typing import List, Dict, Any
from loguru import logger
import pandas as pd
from collections import defaultdict

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.utils.date.date_utils import DateUtils
from core.infra.project_context import ConfigManager


class KlineHandler(BaseHandler):
    """
    K线数据 Handler
    
    以股票为单位处理，每个股票创建 4 个 API Job：
    1. get_daily_kline - 日线价格和成交量数据
    2. get_weekly_kline - 周线价格和成交量数据
    3. get_monthly_kline - 月线价格和成交量数据
    4. get_daily_basic - 基本面指标（PE、PB、换手率、市值等）
    
    优势：
    - daily_basic 只调用一次，减少 API 调用次数（从 6N 降到 4N）
    - 逻辑更清晰（一个股票的所有数据一起处理）
    """
    
    def __init__(self, data_source_name: str, schema, config, providers: Dict[str, BaseProvider]):
        super().__init__(data_source_name, schema, config, providers)
        # 用于增量保存的已保存股票集合（避免重复保存）
        self._saved_stocks = set()
        # 调试模式：限制处理的股票数量
        if hasattr(config, "get"):
            self._debug_limit_stocks = config.get("debug_limit_stocks", None)
        else:
            self._debug_limit_stocks = getattr(config, "debug_limit_stocks", None) if hasattr(config, "debug_limit_stocks") else None
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：为每个股票创建 4 个 ApiJob
        
        Args:
            context: 执行上下文
            apis: 原始 ApiJob 列表（从 config 构建，包含 daily_kline, weekly_kline, monthly_kline, daily_basic）
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表（每个股票 4 个 ApiJob）
        """
        # 重置已保存股票集合
        self._saved_stocks = set()
        
        # 获取股票列表
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("股票列表为空，无法创建 K 线数据获取任务")
            return apis
        
        # 调试模式：限制股票数量
        if self._debug_limit_stocks and self._debug_limit_stocks > 0:
            original_count = len(stock_list)
            stock_list = stock_list[:self._debug_limit_stocks]
            logger.warning(f"🔧 [调试模式] 限制股票数量: {original_count} -> {len(stock_list)} 只股票")
        
        # 获取最新交易日，并计算每个周期的结束日期
        latest_trading_date = context.get("latest_completed_trading_date")
        if not latest_trading_date:
            data_manager = context.get("data_manager")
            if data_manager:
                try:
                    latest_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
                except Exception as e:
                    logger.warning(f"获取最新交易日失败: {e}")
                    latest_trading_date = DateUtils.get_current_date_str()
            else:
                latest_trading_date = DateUtils.get_current_date_str()
        
        # 计算每个周期的结束日期
        end_dates = {
            "daily": latest_trading_date,  # 日线：使用最新交易日
            "weekly": DateUtils.get_previous_week_end(latest_trading_date),  # 周线：上个完整周
            "monthly": DateUtils.get_previous_month_end(latest_trading_date),  # 月线：上个完整月
        }
        context["end_dates"] = end_dates
        
        # 查询数据库获取每个股票在 3 个周期的最新日期
        stock_latest_dates_by_term = self._query_stock_latest_dates(context, stock_list)
        context["stock_latest_dates_by_term"] = stock_latest_dates_by_term
        
        # 构建 API name 到 base_api 的映射
        api_map = {api.api_name: api for api in apis}
        
        expanded_apis = []
        
        # 为每个股票创建 4 个 ApiJob
        for stock in stock_list:
            stock_id = stock.get("ts_code") or stock.get("id")
            if not stock_id:
                continue
            
            # 获取该股票在 3 个周期的最新日期
            stock_dates = stock_latest_dates_by_term.get(stock_id, {})
            
            # 为每个周期计算 start_date，并判断是否需要更新
            start_dates = {}
            
            for term in ["daily", "weekly", "monthly"]:
                latest_date = stock_dates.get(term)
                end_date = end_dates.get(term)
                
                if latest_date:
                    # 已有数据，检查是否需要更新
                    if term == "weekly":
                        # 周线：只有当时间间隔 >= 1 周时才更新
                        time_gap_weeks = DateUtils.get_duration_in_days(latest_date, end_date) // 7
                        if time_gap_weeks < 1:
                            continue
                    elif term == "monthly":
                        # 月线：只有当时间间隔 >= 1 个月时才更新
                        from datetime import datetime
                        latest_dt = DateUtils.parse_yyyymmdd(latest_date)
                        end_dt = DateUtils.parse_yyyymmdd(end_date)
                        year1, month1 = latest_dt.year, latest_dt.month
                        year2, month2 = end_dt.year, end_dt.month
                        month_diff = (year2 - year1) * 12 + (month2 - month1)
                        if end_dt.day < latest_dt.day:
                            month_diff -= 1
                        if month_diff < 1:
                            continue
                    
                    # 从最新日期 + 1 天开始（增量更新）
                    start_date = DateUtils.get_date_after_days(latest_date, 1)
                    # 如果开始日期已经大于等于结束日期，说明数据已经是最新的，跳过该周期
                    if start_date > end_date:
                        continue
                else:
                    # 新股票，使用默认开始日期（全量更新）
                    start_date = ConfigManager.get_default_start_date()
                
                start_dates[term] = start_date
            
            # 如果所有周期都跳过，则跳过该股票
            if not start_dates:
                continue
            
            # 为每个周期创建 K-line ApiJob
            term_to_api = {
                "daily": "daily_kline",
                "weekly": "weekly_kline",
                "monthly": "monthly_kline"
            }
            
            for term, api_name in term_to_api.items():
                if term not in start_dates:
                    continue
                
                base_api = api_map.get(api_name)
                if not base_api:
                    continue
                
                new_api = ApiJob(
                    api_name=base_api.api_name,
                    provider_name=base_api.provider_name,
                    method=base_api.method,
                    params={
                        **base_api.params,
                        "ts_code": stock_id,
                        "start_date": start_dates[term],
                        "end_date": end_dates[term],
                    },
                    api_params=base_api.api_params,
                    depends_on=base_api.depends_on,
                    rate_limit=base_api.rate_limit,
                    job_id=f"kline_{stock_id}_{term}",
                )
                expanded_apis.append(new_api)
            
            # 创建 daily_basic ApiJob（只调用一次）
            if start_dates:
                # 找到最小的 start_date 和最大的 end_date
                min_start_date = min(start_dates.values())
                max_end_date = max(end_dates.get(term, "") for term in start_dates.keys())
                
                # 如果 daily 需要更新，优先使用 daily 的日期范围
                if "daily" in start_dates:
                    basic_start_date = start_dates["daily"]
                    basic_end_date = end_dates["daily"]
                else:
                    basic_start_date = min_start_date
                    basic_end_date = max_end_date
                
                base_api = api_map.get("daily_basic")
                if base_api:
                    new_api = ApiJob(
                        api_name=base_api.api_name,
                        provider_name=base_api.provider_name,
                        method=base_api.method,
                        params={
                            **base_api.params,
                            "ts_code": stock_id,
                            "start_date": basic_start_date,
                            "end_date": basic_end_date,
                        },
                        api_params=base_api.api_params,
                        depends_on=base_api.depends_on,
                        rate_limit=base_api.rate_limit,
                        job_id=f"kline_{stock_id}_daily_basic",
                    )
                    expanded_apis.append(new_api)
        
        logger.info(f"✅ 为 {len(set(api.job_id.split('_')[1] for api in expanded_apis if api.job_id.startswith('kline_')))} 只股票生成了 K 线数据获取任务，共 {len(expanded_apis)} 个 ApiJob")
        return expanded_apis
    
    def _query_stock_latest_dates(self, context: Dict[str, Any], stock_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """
        查询数据库获取每个股票在 3 个周期的最新日期
        
        Args:
            context: 执行上下文
            stock_list: 股票列表
            
        Returns:
            Dict[str, Dict[str, str]]: {stock_id: {term: latest_date}}
        """
        stock_latest_dates_by_term = {}
        data_manager = context.get("data_manager")
        
        if not data_manager or not stock_list:
            return stock_latest_dates_by_term
        
        try:
            kline_model = data_manager.get_table("sys_stock_kline_daily")
            
            # 使用批量查询：一次性获取所有股票的所有周期的最新记录
            try:
                all_latest_records = kline_model.load_latest_records(
                    date_field='date',
                    primary_keys=['id', 'term']
                )
                
                if len(all_latest_records) == 0:
                    logger.warning("⚠️  load_latest_records 返回空结果，尝试手动查询验证...")
                    manual_query = """
                        SELECT t1.* 
                        FROM stock_kline t1
                        INNER JOIN (
                            SELECT id, term, MAX(date) as max_date
                            FROM stock_kline
                            GROUP BY id, term
                        ) t2 
                        ON t1.id = t2.id
                        AND t1.term = t2.term
                        AND t1.date = t2.max_date
                    """
                    manual_result = kline_model.execute_raw_query(manual_query)
                    if manual_result:
                        all_latest_records = manual_result
            except Exception as e:
                logger.error(f"❌ 查询最新日期失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                all_latest_records = []
            
            # 构建股票 ID 集合
            stock_id_set = set()
            for stock in stock_list:
                ts_code = stock.get("ts_code")
                stock_id = stock.get("id")
                final_id = ts_code or stock_id
                if final_id:
                    stock_id_set.add(final_id)
            
            # 整理数据：只保留传入股票列表中的股票
            for record in all_latest_records:
                stock_id = record.get('id')
                term = record.get('term')
                latest_date = record.get('date')
                
                if not stock_id or not term or not latest_date:
                    continue
                
                if stock_id in stock_id_set:
                    if stock_id not in stock_latest_dates_by_term:
                        stock_latest_dates_by_term[stock_id] = {}
                    stock_latest_dates_by_term[stock_id][term] = latest_date
            
            logger.info(f"📊 查询完成：匹配到 {len(stock_latest_dates_by_term)} 只股票有历史数据")
        except Exception as e:
            logger.error(f"❌ 查询股票最新日期失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return stock_latest_dates_by_term
    
    def on_after_execute_job_batch_for_single_stock(
        self, 
        context: Dict[str, Any],
        job_bundle: ApiJobBundle, 
        fetched_data: Dict[str, Any]
    ):
        """
        执行 job batch 后的钩子：按股票分组保存数据
        
        由于基类将所有 apis 打包成一个 batch，我们需要在这里按股票分组处理数据
        
        注意：此处的保存逻辑是按实体（股票）逐个保存，属于执行期保存模式。
        如果未来需要将 save 逻辑完全抽离到上层，可以移除此处的保存调用。
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法保存 K 线数据")
            return
        
        # 按股票分组处理数据
        stock_data_map = self._process_fetched_data_by_stock(fetched_data, job_batch.api_jobs)
        
        # 保存每个股票的数据
        for stock_id, records in stock_data_map.items():
            if stock_id in self._saved_stocks:
                continue
            
            if not records:
                continue
            
            try:
                count = data_manager.stock.kline.save(records)
                logger.info(f"✅ 股票 {stock_id} K 线数据保存完成，共 {len(records)} 条记录（包含所有周期），实际保存 {count} 条")
                self._saved_stocks.add(stock_id)
            except Exception as e:
                logger.error(f"❌ 保存股票 {stock_id} K 线数据失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    def _process_fetched_data_by_stock(
        self, 
        fetched_data: Dict[str, Any],
        api_jobs: List[ApiJob]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        按股票分组处理抓取的数据，合并 K 线数据和 daily_basic 数据
        
        Args:
            fetched_data: {job_id: result} 格式的数据
            api_jobs: ApiJob 列表
            
        Returns:
            Dict[str, List[Dict]]: 按股票分组的记录，格式为 {stock_id: [records]}
        """
        stock_data_map = defaultdict(list)  # {stock_id: [records]}
        
        # 构建 job_id 到 stock_id 和 api_name 的映射
        job_info_map = {}  # {job_id: (stock_id, api_name, term)}
        for api_job in api_jobs:
            job_id = api_job.job_id
            if not job_id or not job_id.startswith("kline_"):
                continue
            
            parts = job_id.split("_")
            if len(parts) < 3:
                continue
            
            stock_id = parts[1]
            api_name = api_job.api_name or api_job.method
            
            # 判断 term
            if "daily_basic" in job_id:
                term = None
            elif "daily" in job_id:
                term = "daily"
            elif "weekly" in job_id:
                term = "weekly"
            elif "monthly" in job_id:
                term = "monthly"
            else:
                term = None
            
            job_info_map[job_id] = (stock_id, api_name, term)
        
        # 按股票分组处理
        stock_basic_map = {}  # {stock_id: basic_df}
        
        # 先收集所有 daily_basic 数据
        for job_id, (stock_id, api_name, term) in job_info_map.items():
            if term is None and "daily_basic" in api_name:
                result = fetched_data.get(job_id)
                if result is not None:
                    if not isinstance(result, pd.DataFrame):
                        basic_df = pd.DataFrame(result) if result else pd.DataFrame()
                    else:
                        basic_df = result
                    if not basic_df.empty:
                        stock_basic_map[stock_id] = basic_df
        
        # 处理每个周期的 K 线数据
        term_mapping = {
            "get_daily_kline": "daily",
            "get_weekly_kline": "weekly",
            "get_monthly_kline": "monthly",
        }
        
        for job_id, (stock_id, api_name, term) in job_info_map.items():
            if term is None:
                continue  # daily_basic 已经处理过了
            
            # 获取该周期的 K 线数据
            kline_result = fetched_data.get(job_id)
            if kline_result is None:
                continue
            
            if not isinstance(kline_result, pd.DataFrame):
                kline_df = pd.DataFrame(kline_result) if kline_result else pd.DataFrame()
            else:
                kline_df = kline_result
            
            if kline_df.empty:
                continue
            
            # 获取 daily_basic 数据
            basic_df = stock_basic_map.get(stock_id)
            if basic_df is None or basic_df.empty:
                logger.warning(f"⚠️  [{stock_id}] [{term}] daily_basic 数据为空，跳过保存，等待下次重试")
                continue
            
            # 合并该周期的 K 线数据和 daily_basic 数据
            merged_df = self._merge_kline_and_basic(kline_df, basic_df, stock_id, term)
            
            if merged_df is not None and not merged_df.empty:
                # 转换为字典列表
                records = merged_df.to_dict('records')
                # 使用统一 helper 清理 NaN 值
                records = self.clean_nan_in_records(records, default=None)
                stock_data_map[stock_id].extend(records)
        
        return stock_data_map
    
    def _merge_kline_and_basic(self, kline_df: pd.DataFrame, basic_df: pd.DataFrame, stock_id: str, term: str) -> pd.DataFrame:
        """
        合并 K 线和 daily_basic 数据，并处理缺失值
        
        Args:
            kline_df: K 线数据
            basic_df: daily_basic 数据
            stock_id: 股票代码
            term: K 线周期
            
        Returns:
            合并后的 DataFrame
        """
        if kline_df.empty:
            return None
        
        # 字段映射（K 线数据）
        kline_mapped = self._map_kline_fields(kline_df, stock_id)
        
        # 字段映射（daily_basic 数据）
        basic_mapped = self._map_basic_fields(basic_df, stock_id) if not basic_df.empty else pd.DataFrame()
        
        # 移除 basic_mapped 中的 close 字段（使用 K-line 的 close 更准确）
        if not basic_mapped.empty and 'close' in basic_mapped.columns:
            basic_mapped = basic_mapped.drop(columns=['close'])
        
        # 合并数据
        if basic_mapped.empty:
            logger.warning(f"⚠️  [{stock_id}] [{term}] daily_basic 数据为空，跳过保存，等待下次重试")
            return None
        
        # LEFT JOIN 合并（保留所有 K 线数据）
        merged = pd.merge(
            kline_mapped, 
            basic_mapped, 
            on=['id', 'date'], 
            how='left', 
            suffixes=('', '_basic')
        )
        
        # 前向填充缺失值（只在有数据的范围内填充）
        basic_columns = [
            'turnover_rate', 'free_turnover_rate', 'volume_ratio',
            'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm',
            'dv_ratio', 'dv_ttm',
            'total_share', 'float_share', 'free_share',
            'total_market_value', 'circ_market_value'
        ]
        
        # 按日期排序
        merged = merged.sort_values('date')
        
        # 找到 basic_mapped 的日期范围（有数据的范围）
        if not basic_mapped.empty:
            basic_min_date = basic_mapped['date'].min()
            basic_max_date = basic_mapped['date'].max()
            
            # 只在有数据的范围内使用 ffill
            for col in basic_columns:
                if col in merged.columns:
                    mask = (merged['date'] >= basic_min_date) & (merged['date'] <= basic_max_date)
                    if mask.any():
                        merged.loc[mask, col] = merged.loc[mask, col].ffill()
                        if basic_mapped[col].notna().any():
                            first_valid = basic_mapped[col].dropna().iloc[0]
                            merged.loc[mask, col] = merged.loc[mask, col].fillna(first_valid)
                    # 对于填充后仍然为 NaN 的字段，使用默认值 0
                    if merged[col].isna().any():
                        merged[col] = merged[col].fillna(0.0)
                    # 对于 basic_mapped 日期范围之前的数据，使用默认值 0
                    before_mask = merged['date'] < basic_min_date
                    if before_mask.any():
                        merged.loc[before_mask, col] = 0.0
        else:
            # 如果没有 basic 数据，所有 basic 字段使用默认值 0
            for col in basic_columns:
                if col in merged.columns:
                    merged[col] = 0.0
        
        # 添加 term 字段
        merged['term'] = term
        
        # 清理数据：移除带 _basic 后缀的列
        columns_to_drop = [col for col in merged.columns if col.endswith('_basic')]
        if columns_to_drop:
            merged = merged.drop(columns=columns_to_drop)
        
        # 处理 NaN 值：将 NaN 转换为 None
        for col in merged.columns:
            merged[col] = merged[col].where(pd.notna(merged[col]), None)
        
        return merged
    
    def _map_kline_fields(self, df: pd.DataFrame, stock_id: str) -> pd.DataFrame:
        """
        映射 K 线字段
        """
        if df.empty:
            return pd.DataFrame()
        
        # 字段映射
        mapping = {
            'ts_code': 'id',
            'trade_date': 'date',
            'open': 'open',
            'high': 'highest',
            'low': 'lowest',
            'close': 'close',
            'pre_close': 'pre_close',
            'change': 'price_change_delta',
            'pct_chg': 'price_change_rate_delta',
            'vol': 'volume',
            'amount': 'amount',
        }
        
        # 重命名列
        mapped_df = df.rename(columns=mapping)
        
        # 确保 id 字段存在
        if 'id' not in mapped_df.columns:
            mapped_df['id'] = stock_id
        
        # 类型转换
        numeric_cols = ['open', 'highest', 'lowest', 'close', 'pre_close', 
                       'price_change_delta', 'price_change_rate_delta', 'amount']
        int_cols = ['volume']
        
        for col in numeric_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce').fillna(0.0)
        
        for col in int_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce').fillna(0).astype(int)
        
        return mapped_df
    
    def _map_basic_fields(self, df: pd.DataFrame, stock_id: str) -> pd.DataFrame:
        """
        映射 daily_basic 字段
        """
        if df.empty:
            return pd.DataFrame()
        
        # 字段映射
        mapping = {
            'ts_code': 'id',
            'trade_date': 'date',
            'turnover_rate': 'turnover_rate',
            'turnover_rate_f': 'free_turnover_rate',
            'volume_ratio': 'volume_ratio',
            'pe': 'pe',
            'pe_ttm': 'pe_ttm',
            'pb': 'pb',
            'ps': 'ps',
            'ps_ttm': 'ps_ttm',
            'dv_ratio': 'dv_ratio',
            'dv_ttm': 'dv_ttm',
            'total_share': 'total_share',
            'float_share': 'float_share',
            'free_share': 'free_share',
            'total_mv': 'total_market_value',
            'circ_mv': 'circ_market_value',
        }
        
        # 重命名列
        mapped_df = df.rename(columns=mapping)
        
        # 确保 id 字段存在
        if 'id' not in mapped_df.columns:
            mapped_df['id'] = stock_id
        
        # 类型转换
        numeric_cols = ['turnover_rate', 'free_turnover_rate', 'volume_ratio',
                       'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm',
                       'dv_ratio', 'dv_ttm',
                       'total_market_value', 'circ_market_value']
        int_cols = ['total_share', 'float_share', 'free_share']
        
        for col in numeric_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce').fillna(0.0)
        
        for col in int_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce').fillna(0).astype(int)
        
        return mapped_df
    
    def _normalize_data(self, context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据：覆盖基类方法，因为数据已经在 on_after_execute_job_batch_for_single_stock 中保存
        
        这里只返回空数据，避免重复处理
        """
        # 数据已经在 on_after_execute_job_batch_for_single_stock 中按股票逐个保存
        # 这里不需要再次处理，返回空数据即可
        return {"data": []}
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：这里只做日志，不再统一写库
        
        K 线数据的落库已经在 on_after_execute_job_batch_for_single_stock 中
        按股票粒度完成，避免重复保存
        """
        data_list = normalized_data.get("data") or []
        logger.info(f"✅ K 线数据标准化完成（按股票已分别保存），总记录数: {len(data_list)}")
        return normalized_data
