"""
复权因子事件 Handler（新算法 - 批量扫描版）

根据优化方案，实现高效的批量扫描和更新流程：
0. CSV导入（如果表为空）
1. 批量查询超过N天未更新的股票
2. 多线程调用 Tushare adj_factor 预筛选（找出有因子变化的股票）
3. 为有变化的股票生成 tasks（Tushare adj_factor + daily_kline + EastMoney QFQ）
4. 保存数据
5. 处理新股票的第一天
6. 季度CSV导出
"""
from typing import List, Dict, Any, Optional, Set
from loguru import logger
import pandas as pd
import requests
import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.data_source.data_source_handler import BaseDataSourceHandler
from app.data_source.api_job import DataSourceTask, ApiJob
from app.data_source.providers.provider_instance_pool import ProviderInstancePool
from utils.date.date_utils import DateUtils


class AdjFactorEventHandler(BaseDataSourceHandler):
    """
    复权因子事件 Handler（新算法 - 批量扫描版）
    
    特点：
    - CSV缓存：空表时从CSV快速恢复
    - 批量筛选：一次SQL查询找出需要更新的股票
    - 预筛选优化：只对有因子变化的股票调用东方财富API
    - 多线程支持：预筛选和精确计算都支持多线程
    - 季度CSV导出：定期备份数据
    """
    
    # 类属性（必须定义）
    data_source = "adj_factor_event"
    renew_type = "incremental"  # 增量更新
    description = "获取复权因子事件数据（只存储除权日）"
    dependencies = ["stock_list", "kline"]  # 依赖股票列表和K线数据
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)
        # 从 params 读取配置
        self.update_threshold_days = params.get('update_threshold_days', 15)  # 默认15天
        self.max_workers = params.get('max_workers', 10)  # 最大线程数
        # 东方财富API限流：60次/分钟（需要手动控制）
        self.eastmoney_rate_limit = 60  # 每分钟60次
        self.eastmoney_min_interval = 60.0 / 60.0  # 每次请求间隔（秒）
        self._last_eastmoney_request_time = 0.0
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段（步骤0-2）
        
        步骤0：如果表为空，尝试从CSV导入
        步骤1：批量查询超过N天未更新的股票
        步骤2：多线程调用 Tushare adj_factor 预筛选（找出有因子变化的股票）
        """
        context = context or {}
        
        if not self.data_manager:
            logger.warning("DataManager 未初始化")
            return context
        
        adj_factor_event_model = self.data_manager.get_model('adj_factor_event')
        kline_model = self.data_manager.get_model('stock_kline')
        
        # ========== 步骤0：CSV导入（如果表为空）==========
        table_was_empty = adj_factor_event_model.is_table_empty()
        if table_was_empty:
            logger.info("📋 步骤 0/6: 复权因子事件表为空，尝试从CSV导入...")
            imported_count = adj_factor_event_model.import_from_csv()
            if imported_count > 0:
                logger.info(f"✅ 从CSV导入 {imported_count} 条记录")
                table_was_empty = False
            else:
                logger.info("ℹ️  未找到CSV文件，继续后续流程")
        
        # ========== 步骤1：确定需要更新的股票集合 ==========
        context_stock_list = context.get("stock_list")
        
        if table_was_empty:
            # 首次构建：如果有传入的 stock_list，则只针对这些股票；否则全量股票
            if context_stock_list:
                stocks_need_update = [s['id'] if isinstance(s, dict) else s for s in context_stock_list]
                logger.info(f"📋 步骤 1/6: 空表首次构建，使用传入的 {len(stocks_need_update)} 只股票进行全量计算")
            else:
                logger.info("📋 步骤 1/6: 空表首次构建，使用全部活跃股票进行全量计算...")
                stock_service = self.data_manager.get_data_service('stock_related.stock')
                if stock_service:
                    all_stocks = stock_service.load_stock_list(filtered=True)
                    stocks_need_update = [s['id'] for s in all_stocks]
                else:
                    stocks_need_update = []
        elif context_stock_list:
            # 表不为空，但有传入的 stock_list，检查这些股票是否有数据
            # 如果没有数据，也需要首次构建
            stocks_need_update = []
            for s in context_stock_list:
                stock_id = s['id'] if isinstance(s, dict) else s
                stock_events = adj_factor_event_model.load("id = %s", (stock_id,), limit=1)
                if not stock_events:
                    # 该股票没有数据，需要首次构建
                    stocks_need_update.append(stock_id)
            
            if stocks_need_update:
                logger.info(f"📋 步骤 1/6: 检测到 {len(stocks_need_update)} 只股票没有数据，进行首次构建")
            else:
                # 所有股票都有数据，走正常增量模式
                logger.info(f"📋 步骤 1/6: 查询超过 {self.update_threshold_days} 天未更新的股票...")
                stocks_need_update = adj_factor_event_model.load_stocks_need_update(self.update_threshold_days)
        else:
            # 正常增量模式：只处理超过 N 天未更新的股票
            logger.info(f"📋 步骤 1/6: 查询超过 {self.update_threshold_days} 天未更新的股票...")
            stocks_need_update = adj_factor_event_model.load_stocks_need_update(self.update_threshold_days)
        
        if not stocks_need_update:
            logger.info("ℹ️  没有股票需要更新")
            context["stocks_with_changes"] = []
            return context
        
        logger.info(f"✅ 查询到 {len(stocks_need_update)} 只股票需要更新")
        
        # 获取最新交易日
        latest_trading_date = self.data_manager.get_latest_trading_date()
        if not latest_trading_date:
            latest_trading_date = DateUtils.get_current_date_str()
        
        # 获取每只股票的最新 event_date 和第一根K线日期
        stock_info_map = {}
        for stock_id in stocks_need_update:
            latest_event = adj_factor_event_model.load_latest_factor(stock_id)
            stock_info_map[stock_id] = {
                'latest_event_date': latest_event['event_date'] if latest_event else None,
                'first_kline_date': None,  # 稍后批量查询
            }
        
        # 批量查询第一根K线日期（仅针对需要更新的股票）
        first_kline_records = kline_model.load_first_kline_records(stock_ids=stocks_need_update)
        first_kline_map = {r['id']: r['date'] for r in first_kline_records}
        for stock_id in stock_info_map:
            stock_info_map[stock_id]['first_kline_date'] = first_kline_map.get(stock_id)
        
        context["stock_info_map"] = stock_info_map
        context["latest_trading_date"] = latest_trading_date
        
        # ========== 步骤2：多线程预筛选（找出有因子变化的股票）==========
        logger.info(f"📋 步骤 2/6: 多线程预筛选（最多 {self.max_workers} 个线程）...")
        stocks_with_changes = self._prefilter_stocks_with_changes(
            stocks_need_update, 
            stock_info_map, 
            latest_trading_date
        )
        
        logger.info(f"✅ 预筛选完成，{len(stocks_with_changes)} 只股票有复权事件")
        context["stocks_with_changes"] = stocks_with_changes
        
        return context
    
    def _prefilter_stocks_with_changes(
        self, 
        stock_ids: List[str], 
        stock_info_map: Dict[str, Dict[str, Any]], 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        多线程预筛选：调用 Tushare adj_factor API，找出“需要全量重算”的股票
        
        Returns:
            List[Dict]: 有变化的股票列表，每个元素包含：
                - stock_id: 股票代码
                - first_kline_date: 第一根K线日期（用于确定全量重算起点）
        """
        # 获取 Tushare Provider
        provider_pool = ProviderInstancePool()
        tushare_provider = provider_pool.get_provider('tushare')
        
        if not tushare_provider:
            logger.error("无法获取 Tushare Provider")
            return []
        
        stocks_with_changes = []
        
        def check_stock(stock_id: str) -> Optional[Dict[str, Any]]:
            """检查单只股票在最近一段时间内是否有因子变化（用来决定是否需要全量重算）"""
            try:
                stock_info = stock_info_map.get(stock_id, {})
                latest_event_date = stock_info.get('latest_event_date')
                first_kline_date = stock_info.get('first_kline_date')
                
                # 确定查询起始日期
                from datetime import date
                if latest_event_date:
                    # 处理 datetime.date 类型
                    if isinstance(latest_event_date, date):
                        start_date = latest_event_date.strftime('%Y%m%d')
                    elif isinstance(latest_event_date, str):
                        start_date = DateUtils.yyyy_mm_dd_to_yyyymmdd(latest_event_date) if '-' in latest_event_date else latest_event_date
                    else:
                        start_date = str(latest_event_date).replace('-', '')
                elif first_kline_date:
                    # 处理 datetime.date 类型
                    if isinstance(first_kline_date, date):
                        start_date = first_kline_date.strftime('%Y%m%d')
                    elif isinstance(first_kline_date, str):
                        start_date = DateUtils.yyyy_mm_dd_to_yyyymmdd(first_kline_date) if '-' in first_kline_date else first_kline_date
                    else:
                        start_date = str(first_kline_date).replace('-', '')
                else:
                    start_date = "20080101"  # 默认起始日期
                
                end_date_ymd = DateUtils.yyyy_mm_dd_to_yyyymmdd(end_date) if '-' in end_date else end_date
                
                if start_date > end_date_ymd:
                    return None
                
                # 调用 Tushare API
                adj_factor_df = tushare_provider.get_adj_factor(
                    ts_code=stock_id,
                    start_date=start_date,
                    end_date=end_date_ymd
                )
                
                if adj_factor_df is None or adj_factor_df.empty:
                    return None
                
                # 只要在最近一段时间内发生过因子变化，就标记该股票需要“全量重算”
                changing_dates = self._get_factor_changing_dates(adj_factor_df)
                if changing_dates:
                    return {
                        'stock_id': stock_id,
                        'first_kline_date': first_kline_date,
                    }
                
                return None
                
            except Exception as e:
                logger.warning(f"预筛选股票 {stock_id} 失败: {e}")
                return None
        
        # 多线程执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(check_stock, stock_id): stock_id for stock_id in stock_ids}
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % 100 == 0:
                    logger.debug(f"预筛选进度: {completed}/{len(stock_ids)}")
                
                result = future.result()
                if result:
                    stocks_with_changes.append(result)
        
        return stocks_with_changes
    
    def _get_factor_changing_dates(self, adj_factor_df: pd.DataFrame) -> List[str]:
        """
        找出复权因子变化的日期
        
        Args:
            adj_factor_df: Tushare adj_factor API 返回的 DataFrame
        
        Returns:
            List[str]: 因子变化的日期列表（YYYYMMDD格式）
        """
        if adj_factor_df is None or adj_factor_df.empty:
            return []
        
        adj_factor_df = adj_factor_df.sort_values('trade_date', ascending=True)
        
        changing_dates = []
        prev_factor = None
        
        for _, row in adj_factor_df.iterrows():
            current_factor = float(row.get('adj_factor', 0))
            trade_date = str(row.get('trade_date', ''))
            
            if not trade_date:
                continue
            
            # 只有当因子真正发生变化时才记录日期（考虑浮点数精度）
            if prev_factor is not None and abs(current_factor - prev_factor) > 1e-6:
                changing_dates.append(trade_date)
            
            prev_factor = current_factor
        
        return changing_dates
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """
        生成获取复权因子事件的 Tasks（步骤3）
        
        只为有因子变化的股票生成 tasks，每个 task 包含：
        - Tushare adj_factor API（获取复权因子）
        - Tushare daily_kline API（获取原始收盘价）
        - EastMoney API（获取前复权价格，用于计算 constantDiff）
        """
        context = context or {}
        stocks_with_changes = context.get("stocks_with_changes", [])
        latest_trading_date = context.get("latest_trading_date")
        
        if not stocks_with_changes:
            logger.info("没有股票有复权事件，无需生成 tasks")
            return []
        
        if not latest_trading_date:
            latest_trading_date = self.data_manager.get_latest_trading_date() if self.data_manager else DateUtils.get_current_date_str()
        
        tasks = []
        stock_info_map = context.get("stock_info_map", {})
        
        # 为了后续计算 F(T)，在上下文中记录每只股票的最新复权因子
        latest_factors: Dict[str, float] = context.get("latest_factors", {})
        
        # 获取 Tushare Provider，用于全量查询复权因子序列
        provider_pool = ProviderInstancePool()
        tushare_provider = provider_pool.get_provider('tushare')
        if not tushare_provider:
            logger.error("无法获取 Tushare Provider")
            return []
        
        end_date_ymd = DateUtils.yyyy_mm_dd_to_yyyymmdd(latest_trading_date) if '-' in latest_trading_date else latest_trading_date
        
        for stock_info in stocks_with_changes:
            stock_id = stock_info['stock_id']
            info = stock_info_map.get(stock_id, {})
            first_kline_date = info.get('first_kline_date')
            
            # 全量重算起点：优先使用第一根K线日期，否则使用默认起点
            if first_kline_date:
                start_date_full = DateUtils.yyyy_mm_dd_to_yyyymmdd(first_kline_date) if '-' in first_kline_date else first_kline_date
            else:
                start_date_full = "20080101"
            
            if start_date_full > end_date_ymd:
                continue
            
            # 全量获取该股票从起点到最新交易日的复权因子序列
            adj_factor_df_full = tushare_provider.get_adj_factor(
                ts_code=stock_id,
                start_date=start_date_full,
                end_date=end_date_ymd
            )
            if adj_factor_df_full is None or adj_factor_df_full.empty:
                continue
            
            # 记录最新复权因子 F(T)，供 after_execute 使用
            adj_factor_df_full_sorted = adj_factor_df_full.sort_values('trade_date', ascending=True)
            latest_factor = float(adj_factor_df_full_sorted.iloc[-1]['adj_factor'])
            latest_factors[stock_id] = latest_factor
            
            # 计算该股票全历史的所有复权事件日期
            changing_dates_full = self._get_factor_changing_dates(adj_factor_df_full_sorted)
            
            # 为每个事件日期构建 F(T) 映射：event_date -> 下一个事件的因子（或最新因子）
            # 这样在 after_execute 中可以为每个事件使用正确的 F(T)
            # 注意：F(T) 应该是该事件日之后的下一个复权事件日的因子，而不是下一个交易日的因子
            event_factor_map: Dict[str, float] = {}
            for i, event_date_ymd in enumerate(changing_dates_full):
                # 获取当前事件日的因子
                current_event_row = adj_factor_df_full_sorted[adj_factor_df_full_sorted['trade_date'] == event_date_ymd]
                if current_event_row.empty:
                    event_factor_map[event_date_ymd] = latest_factor
                    continue
                
                current_factor = float(current_event_row.iloc[0]['adj_factor'])
                
                # 找到该事件日之后的下一个因子变化的日期（下一个复权事件日）
                current_event_idx = adj_factor_df_full_sorted.index.get_loc(current_event_row.index[0])
                next_factor = None
                
                # 从下一个交易日开始查找因子变化
                for j in range(current_event_idx + 1, len(adj_factor_df_full_sorted)):
                    next_row = adj_factor_df_full_sorted.iloc[j]
                    next_row_factor = float(next_row['adj_factor'])
                    if next_row_factor != current_factor:
                        # 找到因子变化，使用这个因子作为 F(T)
                        next_factor = next_row_factor
                        break
                
                if next_factor is not None:
                    event_factor_map[event_date_ymd] = next_factor
                else:
                    # 没有找到下一个因子变化，使用最新因子
                    event_factor_map[event_date_ymd] = latest_factor
            
            # 将 event_factor_map 存储到 context 中，供 after_execute 使用
            if "event_factor_map" not in context:
                context["event_factor_map"] = {}
            context["event_factor_map"][stock_id] = event_factor_map
            
            # 确保第一根K线日期作为一个事件点（如果不存在于变化列表中）
            if first_kline_date:
                first_kline_ymd = DateUtils.yyyy_mm_dd_to_yyyymmdd(first_kline_date) if '-' in first_kline_date else first_kline_date
                if first_kline_ymd not in changing_dates_full:
                    changing_dates_full.insert(0, first_kline_ymd)
            
            if not changing_dates_full:
                continue
            
            # 为每个复权日期创建一个 task
            for event_date_ymd in changing_dates_full:
                # 1. Tushare adj_factor API
                adj_factor_job = ApiJob(
                    provider_name="tushare",
                    method="get_adj_factor",
                    params={
                        "ts_code": stock_id,
                        "start_date": event_date_ymd,
                        "end_date": event_date_ymd,
                    },
                    job_id=f"{stock_id}_adj_factor_{event_date_ymd}",
                    api_name="get_adj_factor"
                )
                
                # 2. Tushare daily_kline API（获取原始收盘价）
                daily_kline_job = ApiJob(
                    provider_name="tushare",
                    method="get_daily_kline",
                    params={
                        "ts_code": stock_id,
                        "start_date": event_date_ymd,
                        "end_date": event_date_ymd,
                    },
                    job_id=f"{stock_id}_daily_kline_{event_date_ymd}",
                    api_name="get_daily_kline"
                )
                
                # 3. EastMoney API（获取前复权价格）
                eastmoney_secid = self._convert_to_eastmoney_secid(stock_id)
                eastmoney_job = ApiJob(
                    provider_name="eastmoney",
                    method="get_qfq_kline",
                    params={
                        "secid": eastmoney_secid,
                        "end_date": end_date_ymd,
                        "limit": 5000
                    },
                    job_id=f"{stock_id}_eastmoney_{event_date_ymd}",
                    api_name="get_qfq_kline"
                )
                
                task = DataSourceTask(
                    task_id=f"adj_factor_event_{stock_id}_{event_date_ymd}",
                    api_jobs=[adj_factor_job, daily_kline_job, eastmoney_job],
                    description=f"获取 {stock_id} 在 {event_date_ymd} 的复权因子事件",
                )
                tasks.append(task)
        
        logger.info(f"✅ 生成了 {len(tasks)} 个复权因子事件获取任务")
        return tasks
    
    def _convert_to_eastmoney_secid(self, stock_id: str) -> str:
        """
        转换股票代码为东方财富格式
        
        Tushare: 000001.SZ -> 东方财富: 0.000001
        Tushare: 600000.SH -> 东方财富: 1.600000
        """
        if '.' not in stock_id:
            return stock_id
        
        code, market = stock_id.split('.')
        
        if market == 'SZ':
            return f"0.{code}"
        elif market == 'SH':
            return f"1.{code}"
        else:
            logger.warning(f"未知交易所 {market} for {stock_id}")
            return stock_id
    
    async def after_execute(self, task_results: Dict[str, Dict[str, Any]], context: Dict[str, Any] = None):
        """
        执行后处理（步骤4）
        
        处理 API 返回结果，计算 constantDiff，保存到数据库
        """
        context = context or {}
        
        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法保存数据")
            return
        
        adj_factor_event_model = self.data_manager.get_model('adj_factor_event')
        saved_count = 0
        failed_count = 0
        cleared_stocks: Set[str] = set()
        latest_factors: Dict[str, float] = context.get("latest_factors", {})
        
        # task_results 的结构：{task_id: {job_id: result}}
        for task_id, task_result in task_results.items():
            if not task_result:
                failed_count += 1
                continue
            
            # 解析 task_id: adj_factor_event_{stock_id}_{event_date}
            parts = task_id.replace("adj_factor_event_", "").split("_", 1)
            if len(parts) < 2:
                failed_count += 1
                continue
            
            stock_id = parts[0]
            event_date_ymd = parts[1]
            
            try:
                # 首次处理该股票时，删除旧的复权事件记录，实现“全量重算”
                if stock_id not in cleared_stocks:
                    adj_factor_event_model.delete("id = %s", (stock_id,))
                    cleared_stocks.add(stock_id)

                # 获取三个 API 的结果
                adj_factor_result = task_result.get(f"{stock_id}_adj_factor_{event_date_ymd}")
                daily_kline_result = task_result.get(f"{stock_id}_daily_kline_{event_date_ymd}")
                eastmoney_result = task_result.get(f"{stock_id}_eastmoney_{event_date_ymd}")
                
                # 验证必需的数据
                if adj_factor_result is None or adj_factor_result.empty:
                    logger.warning(f"{stock_id} {event_date_ymd}: 复权因子数据为空，跳过")
                    failed_count += 1
                    continue
                
                if daily_kline_result is None or daily_kline_result.empty:
                    logger.warning(f"{stock_id} {event_date_ymd}: 日线数据为空，跳过")
                    failed_count += 1
                    continue
                
                # 提取复权因子
                adj_factor_row = adj_factor_result.iloc[0]
                adj_factor = float(adj_factor_row.get('adj_factor', 0))
                
                if adj_factor == 0:
                    logger.warning(f"{stock_id} {event_date_ymd}: 复权因子为0，跳过")
                    failed_count += 1
                    continue
                
                # 提取原始收盘价
                daily_kline_row = daily_kline_result.iloc[0]
                raw_close = float(daily_kline_row.get('close', 0))
                
                if raw_close == 0:
                    logger.warning(f"{stock_id} {event_date_ymd}: 收盘价为0，跳过")
                    failed_count += 1
                    continue
                
                # 获取该事件日对应的 F(T)（应该是该事件日之后的下一个因子，或最新因子）
                # 优先使用 event_factor_map 中的值（事件日之后的下一个因子）
                event_factor_map = context.get("event_factor_map", {}).get(stock_id, {})
                F_T = event_factor_map.get(event_date_ymd)
                
                # 如果没有找到，fallback 到 latest_factors（当前最新因子）
                if F_T is None:
                    F_T = latest_factors.get(stock_id, adj_factor)
                    logger.warning(f"{stock_id} {event_date_ymd}: 未找到对应的 F(T)，使用最新因子 {F_T}")
                
                # 计算 Tushare 前复权价格
                tushare_qfq = raw_close * adj_factor / F_T
                
                # 从东方财富 API 获取前复权价格
                eastmoney_qfq = self._parse_eastmoney_qfq_price(eastmoney_result, event_date_ymd)
                
                # 计算 qfq_diff
                qfq_diff = 0.0
                if eastmoney_qfq is not None:
                    qfq_diff = eastmoney_qfq - tushare_qfq
                    logger.debug(f"{stock_id} {event_date_ymd}: Tushare_QFQ={tushare_qfq:.2f}, EastMoney_QFQ={eastmoney_qfq:.2f}, Diff={qfq_diff:.4f}")
                else:
                    logger.warning(f"{stock_id} {event_date_ymd}: 无法获取东方财富前复权价格，qfq_diff 设为 0.0")
                
                # 保存到数据库（event_date 使用 YYYYMMDD 格式）
                adj_factor_event_model.save_event(
                    stock_id=stock_id,
                    event_date=event_date_ymd,
                    tushare_factor=adj_factor,
                    qfq_diff=qfq_diff
                )
                saved_count += 1
                logger.debug(f"✅ 保存复权因子事件: {stock_id} {event_date_ymd}, factor={adj_factor:.6f}, diff={qfq_diff:.4f}")
                
            except Exception as e:
                logger.error(f"❌ 处理复权因子事件失败: {stock_id} {event_date_ymd}, {e}")
                failed_count += 1
                import traceback
                traceback.print_exc()
        
        logger.info(f"✅ 复权因子事件处理完成，成功 {saved_count} 条，失败 {failed_count} 条")
    
    def _parse_eastmoney_qfq_price(self, eastmoney_result: Any, event_date_ymd: str) -> Optional[float]:
        """
        解析东方财富 API 返回的前复权价格
        
        Args:
            eastmoney_result: 东方财富 Provider 返回的 JSON 数据（dict）
            event_date_ymd: 日期（YYYYMMDD格式）
        
        Returns:
            前复权收盘价，如果解析失败返回 None
        """
        try:
            # EastMoneyProvider 返回的是 dict
            if not isinstance(eastmoney_result, dict):
                return None
            
            klines = eastmoney_result.get('data', {}).get('klines', [])
            if not klines:
                return None
            
            # 转换日期格式
            target_date = DateUtils.yyyymmdd_to_yyyy_mm_dd(event_date_ymd)
            
            # 查找对应日期的数据
            # klines 格式：["2024-12-15,11.46", "2024-12-14,11.45", ...]
            # 第一个字段是日期（YYYY-MM-DD），第二个字段是收盘价
            for kline_str in klines:
                parts = kline_str.split(',')
                if len(parts) >= 2:
                    date_str = parts[0]
                    close_price = float(parts[1])
                    
                    if date_str == target_date:
                        return close_price
            
            return None
            
        except Exception as e:
            logger.warning(f"解析东方财富 API 数据失败: {e}")
            return None
    
    async def after_normalize(self, normalized_data: Dict[str, Any], context: Dict[str, Any] = None):
        """
        标准化后处理（步骤5-6）
        
        步骤5：处理新股票的第一天（已在 before_fetch 中处理）
        步骤6：季度CSV导出
        """
        context = context or {}
        
        if not self.data_manager:
            return
        
        adj_factor_event_model = self.data_manager.get_model('adj_factor_event')
        
        # ========== 步骤6：季度CSV导出 ==========
        # 检查是否需要导出CSV（每季度一次）
        # 这里简化处理：每次更新后都检查，如果当前季度还没有CSV就导出
        current_csv_name = adj_factor_event_model.get_current_quarter_csv_name()
        current_csv_path = os.path.join(adj_factor_event_model.csv_dir, current_csv_name)
        
        if not os.path.exists(current_csv_path):
            logger.info(f"📋 步骤 6/6: 导出季度CSV...")
            exported_count = adj_factor_event_model.export_to_csv()
            if exported_count > 0:
                logger.info(f"✅ 导出季度CSV完成: {exported_count} 条记录 -> {current_csv_name}")
            else:
                logger.warning("导出季度CSV失败")
        else:
            logger.debug(f"当前季度CSV已存在: {current_csv_name}")
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据（用于兼容框架，实际保存逻辑在 after_execute 中）
        """
        # 数据已在 after_execute 中保存，这里返回空数据
        return {"data": []}
