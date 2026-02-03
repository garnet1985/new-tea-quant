"""
K线数据 Handler

从 Tushare 获取股票 K 线数据（日线/周线/月线），写入 sys_stock_klines。
每日基本面指标（daily_basic）已拆分为 stock_indicators handler，写入 sys_stock_indicators。

以股票为单位处理，每个股票创建 3 个 API Job：daily_kline、weekly_kline、monthly_kline。
在 on_after_execute_job_batch_for_single_stock 中按股票分组保存。
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
    K线数据 Handler，绑定表 sys_stock_klines。
    每个股票 3 个 ApiJob：daily_kline、weekly_kline、monthly_kline。
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
        # 用于增量保存的已保存股票集合（避免重复保存）
        self._saved_stocks = set()
        # 调试模式：限制处理的股票数量
        if hasattr(config, "get"):
            self._debug_limit_stocks = config.get("debug_limit_stocks", None)
        else:
            self._debug_limit_stocks = getattr(config, "debug_limit_stocks", None) if hasattr(config, "debug_limit_stocks") else None
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：为每个股票创建 3 个 ApiJob（daily/weekly/monthly kline）。
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
                    latest_trading_date = DateUtils.get_today_str()
            else:
                latest_trading_date = DateUtils.get_today_str()
        
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
            kline_model = data_manager.get_table("sys_stock_klines")
            
            # 使用批量查询：一次性获取所有股票的所有周期的最新记录
            try:
                all_latest_records = kline_model.load_latests(
                    date_field='date',
                    group_fields=['id', 'term']
                )
                
                if len(all_latest_records) == 0:
                    logger.warning("⚠️  load_latests 返回空结果，尝试手动查询验证...")
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
        stock_data_map = self._process_fetched_data_by_stock(fetched_data, job_bundle.api_jobs)
        
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
        api_jobs: List[ApiJob],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按股票分组处理抓取数据，仅 K 线（daily/weekly/monthly），不合并 daily_basic。"""
        stock_data_map = defaultdict(list)

        job_info_map = {}
        for api_job in api_jobs:
            job_id = api_job.job_id
            if not job_id or not job_id.startswith("kline_"):
                continue
            parts = job_id.split("_")
            if len(parts) < 3:
                continue
            stock_id = parts[1]
            if "daily" in job_id and "daily_basic" not in job_id:
                term = "daily"
            elif "weekly" in job_id:
                term = "weekly"
            elif "monthly" in job_id:
                term = "monthly"
            else:
                continue
            job_info_map[job_id] = (stock_id, term)

        for job_id, (stock_id, term) in job_info_map.items():
            kline_result = fetched_data.get(job_id)
            if kline_result is None:
                continue
            if not isinstance(kline_result, pd.DataFrame):
                kline_df = pd.DataFrame(kline_result) if kline_result else pd.DataFrame()
            else:
                kline_df = kline_result
            if kline_df.empty:
                continue
            kline_mapped = self._map_kline_fields(kline_df, stock_id)
            kline_mapped["term"] = term
            records = kline_mapped.to_dict("records")
            records = self.clean_nan_in_records(records, default=None)
            stock_data_map[stock_id].extend(records)

        return stock_data_map

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
