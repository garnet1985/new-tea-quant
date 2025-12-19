"""
K线数据 Handler

从 Tushare 获取股票 K 线数据（日线/周线/月线）
以股票为单位处理，每个股票创建一个 Task，包含 4 个 API Job：
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
- 在 after_execute 钩子中，按股票分组保存数据
- 每个股票的所有周期数据获取完成后，立即保存该股票的数据（支持多线程）
- 这样可以在多线程环境中，每个线程完成一个股票的数据后立即保存，避免内存占用过大
"""
from typing import List, Dict, Any
from loguru import logger
import pandas as pd
from collections import defaultdict

from app.data_source.data_source_handler import BaseDataSourceHandler
from app.data_source.api_job import DataSourceTask, ApiJob
from utils.date.date_utils import DateUtils


class KlineHandler(BaseDataSourceHandler):
    """
    K线数据 Handler
    
    以股票为单位处理，每个股票创建一个 Task，包含 4 个 API Job：
    1. get_daily_kline - 日线价格和成交量数据
    2. get_weekly_kline - 周线价格和成交量数据
    3. get_monthly_kline - 月线价格和成交量数据
    4. get_daily_basic - 基本面指标（PE、PB、换手率、市值等）
    
    优势：
    - daily_basic 只调用一次，减少 API 调用次数（从 6N 降到 4N）
    - 逻辑更清晰（一个股票的所有数据一起处理）
    - 不需要跨线程缓存机制
    """
    data_source = "kline"
    renew_type = "incremental"
    description = "获取K线数据（包含 K 线和基本面指标），支持 daily/weekly/monthly 周期"
    dependencies = ["stock_list"]
    requires_date_range = True
    
    # 周期映射表
    TERM_MAPPING = {
        "daily": {
            "kline_method": "get_daily_kline",
            "description": "日线数据"
        },
        "weekly": {
            "kline_method": "get_weekly_kline",
            "description": "周线数据"
        },
        "monthly": {
            "kline_method": "get_monthly_kline",
            "description": "月线数据"
        }
    }
    
    def __init__(self, schema, params: dict = None, data_manager=None):
        """初始化 K 线 Handler"""
        super().__init__(schema, params, data_manager)
        # 用于增量保存的已保存任务集合（避免重复保存）
        # 每次 fetch_and_normalize 开始时重置，确保每次运行都是新的状态
        self._saved_tasks = set()
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        1. 从 data_manager 获取股票列表（从数据库读取）
        2. 查询数据库获取每个股票在 3 个周期（daily/weekly/monthly）的最新日期
        3. 计算每个周期需要更新的结束日期
        """
        context = context or {}
        
        # 1. 获取股票列表（从数据库读取，使用过滤规则排除ST、科创板等）
        if "stock_list" not in context:
            if self.data_manager:
                try:
                    # 使用过滤规则，排除ST、科创板等（不是所有股票都需要renew）
                    stock_list = self.data_manager.load_stock_list(filtered=True)
                    context["stock_list"] = stock_list
                    logger.info(f"✅ 从数据库获取股票列表（已过滤），共 {len(stock_list)} 只股票")
                except Exception as e:
                    logger.warning(f"查询股票列表失败: {e}")
                    context["stock_list"] = []
            else:
                logger.warning("data_manager 未设置，无法获取股票列表")
                context["stock_list"] = []
        
        # 2. 获取最新交易日，并计算每个周期的结束日期
        if self.data_manager:
            try:
                latest_trading_date = self.data_manager.get_latest_completed_trading_date()
                
                # 计算每个周期的结束日期
                end_dates = {
                    "daily": latest_trading_date,  # 日线：使用最新交易日
                    "weekly": DateUtils.get_previous_week_end(latest_trading_date),  # 周线：上个完整周
                    "monthly": DateUtils.get_previous_month_end(latest_trading_date),  # 月线：上个完整月
                }
                context["end_dates"] = end_dates
            except Exception as e:
                logger.warning(f"获取结束日期失败: {e}")
                latest_trading_date = DateUtils.get_current_date_str()
                context["end_dates"] = {
                    "daily": latest_trading_date,
                    "weekly": latest_trading_date,
                    "monthly": latest_trading_date,
                }
        
        # 3. 查询数据库获取每个股票在 3 个周期的最新日期（批量查询，避免 O(N×3) 查询）
        stock_latest_dates_by_term = {}  # {stock_id: {term: latest_date}}
        if self.data_manager and context.get("stock_list"):
            try:
                kline_model = self.data_manager.get_model('stock_kline')
                stock_list = context["stock_list"]
                
                # 使用批量查询：一次性获取所有股票的所有周期的最新记录
                # 使用 load_latest_records 方法，它会使用 GROUP BY 和 MAX(date) 来高效查询
                # 注意：load_latest_records 需要指定 primary_keys 和 date_field
                # 这个方法会查询整个表，返回所有 (id, term) 组合的最新记录
                all_latest_records = kline_model.load_latest_records(
                    date_field='date',
                    primary_keys=['id', 'term']  # 按 id 和 term 分组，获取每个组合的最新记录
                )
                
                # 构建股票 ID 集合（用于快速过滤）
                stock_id_set = set()
                for stock in stock_list:
                    stock_id = stock.get("ts_code") or stock.get("id")
                    if stock_id:
                        stock_id_set.add(stock_id)
                
                # 在 Python 中整理数据：只保留传入股票列表中的股票
                # {stock_id: {term: latest_date}}
                for record in all_latest_records:
                    stock_id = record.get('id')
                    term = record.get('term')
                    latest_date = record.get('date')
                    
                    # 只处理传入股票列表中的股票
                    if stock_id in stock_id_set and term and latest_date:
                        if stock_id not in stock_latest_dates_by_term:
                            stock_latest_dates_by_term[stock_id] = {}
                        stock_latest_dates_by_term[stock_id][term] = latest_date
                
                context["stock_latest_dates_by_term"] = stock_latest_dates_by_term
                
                # 统计（只统计传入股票列表中的股票）
                total_stocks = len(stock_list)
                stocks_with_daily = sum(1 for stock_id in stock_id_set if stock_id in stock_latest_dates_by_term and "daily" in stock_latest_dates_by_term[stock_id])
                stocks_with_weekly = sum(1 for stock_id in stock_id_set if stock_id in stock_latest_dates_by_term and "weekly" in stock_latest_dates_by_term[stock_id])
                stocks_with_monthly = sum(1 for stock_id in stock_id_set if stock_id in stock_latest_dates_by_term and "monthly" in stock_latest_dates_by_term[stock_id])
                logger.info(
                    f"✅ 批量查询完成：{total_stocks} 只股票，"
                    f"daily: {stocks_with_daily} 只有数据，"
                    f"weekly: {stocks_with_weekly} 只有数据，"
                    f"monthly: {stocks_with_monthly} 只有数据"
                )
            except Exception as e:
                logger.warning(f"查询数据库获取最新日期失败: {e}")
                context["stock_latest_dates_by_term"] = {}
    
    async def fetch(self, context: Dict[str, Any] = None) -> List['DataSourceTask']:
        """
        生成获取 K 线数据的 Tasks
        
        逻辑：
        1. 从 context 获取股票列表和日期范围
        2. 为每个股票创建一个 Task
        3. 每个 Task 包含 4 个 ApiJob：
           - get_daily_kline - 日线价格和成交量数据
           - get_weekly_kline - 周线价格和成交量数据
           - get_monthly_kline - 月线价格和成交量数据
           - get_daily_basic - 基本面指标（PE、PB、换手率、市值等）
        
        优势：
        - daily_basic 只调用一次，减少 API 调用次数（从 6N 降到 4N）
        - 逻辑更清晰（一个股票的所有数据一起处理）
        """
        context = context or {}
        # 重置已保存任务集合（每次 fetch 开始时重置，确保增量保存状态正确）
        self._saved_tasks = set()
        
        stock_list = context.get("stock_list", [])
        end_dates = context.get("end_dates", {})
        stock_latest_dates_by_term = context.get("stock_latest_dates_by_term", {})
        
        if not stock_list:
            logger.warning("股票列表为空，无法获取 K 线数据")
            return []
        
        if not end_dates:
            raise ValueError(f"{self.__class__.__name__} 需要 end_dates 参数（包含 daily/weekly/monthly 的结束日期）")
        
        tasks = []
        from app.conf.conf import data_default_start_date
        
        for stock in stock_list:
            stock_id = stock.get("ts_code") or stock.get("id")
            stock_name = stock.get("name", "")
            
            if not stock_id:
                continue
            
            # 获取该股票在 3 个周期的最新日期
            stock_dates = stock_latest_dates_by_term.get(stock_id, {})
            
            # 为每个周期计算 start_date，并判断是否需要更新
            start_dates = {}
            skip_stock = True  # 如果所有周期都跳过，则跳过该股票
            
            for term in ["daily", "weekly", "monthly"]:
                latest_date = stock_dates.get(term)
                end_date = end_dates.get(term)
                
                if latest_date:
                    # 已有数据，检查是否需要更新
                    # 对于 weekly/monthly，需要检查时间间隔是否 >= 1 个完整周期
                    if term == "weekly":
                        # 周线：只有当时间间隔 >= 1 周时才更新
                        time_gap_weeks = DateUtils.get_duration_in_days(latest_date, end_date) // 7
                        if time_gap_weeks < 1:
                            continue
                    elif term == "monthly":
                        # 月线：只有当时间间隔 >= 1 个月时才更新
                        # 使用更准确的月份计算方法（参考 legacy 的 time_gap_by）
                        from datetime import datetime
                        latest_dt = DateUtils.parse_yyyymmdd(latest_date)
                        end_dt = DateUtils.parse_yyyymmdd(end_date)
                        year1, month1 = latest_dt.year, latest_dt.month
                        year2, month2 = end_dt.year, end_dt.month
                        month_diff = (year2 - year1) * 12 + (month2 - month1)
                        # 如果天数不足，减一个月
                        if end_dt.day < latest_dt.day:
                            month_diff -= 1
                        if month_diff < 1:
                            continue
                    
                    # 从最新日期 + 1 天开始
                    start_date = DateUtils.get_date_after_days(latest_date, 1)
                    # 如果开始日期已经大于等于结束日期，说明数据已经是最新的，跳过该周期
                    if start_date > end_date:
                        continue
                else:
                    # 新股票，使用默认开始日期
                    start_date = data_default_start_date
                
                start_dates[term] = start_date
                skip_stock = False
            
            # 如果所有周期都跳过，则跳过该股票
            if skip_stock:
                continue
            
            # 创建 Task：包含 4 个 ApiJob
            task_id = f"kline_{stock_id}"
            
            api_jobs = []
            
            # ApiJob 1: daily K-line
            if "daily" in start_dates:
                api_jobs.append(ApiJob(
                    provider_name="tushare",
                    method="get_daily_kline",
                    params={
                        "ts_code": stock_id,
                        "start_date": start_dates["daily"],
                        "end_date": end_dates["daily"],
                    },
                    api_name="get_daily_kline",
                    job_id=f"{task_id}_get_daily_kline",  # 明确指定 job_id，使用 api_name 确保唯一性
                ))
            
            # ApiJob 2: weekly K-line
            if "weekly" in start_dates:
                api_jobs.append(ApiJob(
                    provider_name="tushare",
                    method="get_weekly_kline",
                    params={
                        "ts_code": stock_id,
                        "start_date": start_dates["weekly"],
                        "end_date": end_dates["weekly"],
                    },
                    api_name="get_weekly_kline",
                    job_id=f"{task_id}_get_weekly_kline",  # 明确指定 job_id，使用 api_name 确保唯一性
                ))
            
            # ApiJob 3: monthly K-line
            if "monthly" in start_dates:
                api_jobs.append(ApiJob(
                    provider_name="tushare",
                    method="get_monthly_kline",
                    params={
                        "ts_code": stock_id,
                        "start_date": start_dates["monthly"],
                        "end_date": end_dates["monthly"],
                    },
                    api_name="get_monthly_kline",
                    job_id=f"{task_id}_get_monthly_kline",  # 明确指定 job_id，使用 api_name 确保唯一性
                ))
            
            # ApiJob 4: daily_basic（只调用一次）
            # 注意：即使 weekly/monthly 需要更新，daily_basic 也只需要调用一次
            # 因为 daily_basic 是日线数据，可以用于所有周期
            # 使用所有需要更新的周期中最小的 start_date 和最大的 end_date
            if start_dates:
                # 找到最小的 start_date 和最大的 end_date（在所有需要更新的周期中）
                min_start_date = min(start_dates.values())
                # 找到最大的 end_date
                max_end_date = max(end_dates.get(term, "") for term in start_dates.keys())
                
                # 如果 daily 需要更新，优先使用 daily 的日期范围（更准确）
                # 否则使用所有周期的范围
                if "daily" in start_dates:
                    basic_start_date = start_dates["daily"]
                    basic_end_date = end_dates["daily"]
                else:
                    basic_start_date = min_start_date
                    basic_end_date = max_end_date
                
                api_jobs.append(ApiJob(
                    provider_name="tushare",
                    method="get_daily_basic",
                    params={
                        "ts_code": stock_id,
                        "start_date": basic_start_date,
                        "end_date": basic_end_date,
                    },
                    api_name="get_daily_basic",
                    job_id=f"{task_id}_get_daily_basic",  # 明确指定 job_id，使用 api_name 确保唯一性
                ))
            
            if not api_jobs:
                continue
            
            task = DataSourceTask(
                task_id=task_id,
                api_jobs=api_jobs,
                description=f"获取 {stock_name} ({stock_id}) K 线数据（daily/weekly/monthly + daily_basic）",
            )
            
            tasks.append(task)
        
        # 保存生成的 tasks（用于 normalize 中查找）
        self._generated_tasks = tasks
        
        logger.info(f"✅ 生成了 {len(tasks)} 个 K 线数据获取任务（每个任务包含 3-4 个 API Job）")
        
        return tasks
    
    def _process_task_results(
        self, 
        task_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        处理 Task 执行结果，合并 K 线数据和 daily_basic 数据
        
        公共逻辑：
        - 遍历所有 Task 的结果
        - 每个 Task 包含 3-4 个 API Job（daily/weekly/monthly K-line + daily_basic）
        - 对每个周期的 K 线数据与 daily_basic 进行合并
        - 按股票分组返回处理后的记录
        
        Args:
            task_results: Task 执行结果，格式为 {task_id: {job_id: result}}
            
        Returns:
            Dict[str, List[Dict]]: 按股票分组的记录，格式为 {stock_id: [records]}
        """
        stock_data_map = defaultdict(list)  # {stock_id: [records]}
        
        # 只处理传入的 task_results 中的任务（避免在增量保存时遍历所有任务）
        # 构建 task_id 到 task 的映射
        task_map = {task.task_id: task for task in self._generated_tasks}
        
        # 遍历传入的 task_results（只处理有结果的任务）
        for task_id, task_result in task_results.items():
            if task_id not in task_map:
                continue
            
            task = task_map[task_id]
            stock_id = task.api_jobs[0].params.get("ts_code")
            
            if not stock_id:
                continue
            
            # 通过 api_name 识别每个 job 的类型
            # 构建 job_id 到 api_name 的映射
            # 注意：直接使用 api_job.job_id（已在 DataSourceTask.__post_init__ 中设置或手动指定）
            job_api_map = {}  # {job_id: api_name}
            for api_job in task.api_jobs:
                job_id = api_job.job_id  # 使用 ApiJob 的 job_id（不依赖顺序）
                if job_id:
                    job_api_map[job_id] = api_job.api_name or api_job.method
            
            # 获取 daily_basic 数据（所有周期共享）
            basic_df = None
            for job_id, api_name in job_api_map.items():
                if api_name == "get_daily_basic":
                    basic_result = task_result.get(job_id)
                    if basic_result is not None:
                        if not isinstance(basic_result, pd.DataFrame):
                            basic_df = pd.DataFrame(basic_result) if basic_result else pd.DataFrame()
                        else:
                            basic_df = basic_result
                    break
            
            if basic_df is None or basic_df.empty:
                continue
            
            # 处理每个周期的 K 线数据
            term_mapping = {
                "get_daily_kline": "daily",
                "get_weekly_kline": "weekly",
                "get_monthly_kline": "monthly",
            }
            
            for job_id, api_name in job_api_map.items():
                if api_name == "get_daily_basic":
                    continue  # 已经处理过了
                
                term = term_mapping.get(api_name)
                if not term:
                    continue
                
                # 获取该周期的 K 线数据
                kline_result = task_result.get(job_id)
                if kline_result is None:
                    continue
                
                if not isinstance(kline_result, pd.DataFrame):
                    kline_df = pd.DataFrame(kline_result) if kline_result else pd.DataFrame()
                else:
                    kline_df = kline_result
                
                if kline_df.empty:
                    continue
                
                # 合并该周期的 K 线数据和 daily_basic 数据
                merged_df = self._merge_kline_and_basic(kline_df, basic_df, stock_id, term)
                
                if merged_df is not None and not merged_df.empty:
                    # 转换为字典列表
                    records = merged_df.to_dict('records')
                    # 清理 NaN 值：确保所有 NaN 都转换为 None（MySQL 不支持 NaN）
                    import math
                    for record in records:
                        for key, value in list(record.items()):
                            # 处理各种类型的 NaN
                            if value is None:
                                continue  # None 是合法的，不需要处理
                            elif isinstance(value, float):
                                if math.isnan(value) or pd.isna(value):
                                    record[key] = None
                            elif pd.isna(value):
                                record[key] = None
                            # 处理 numpy 的 NaN
                            elif hasattr(value, '__class__') and str(value.__class__) == "<class 'numpy.float64'>":
                                try:
                                    if math.isnan(float(value)):
                                        record[key] = None
                                except (ValueError, TypeError):
                                    pass
                    stock_data_map[stock_id].extend(records)
        
        return stock_data_map
    
    async def _save_single_task_result(self, task_id: str, task_result: Dict[str, Any], context: Dict[str, Any] = None):
        """
        保存单个任务的结果（增量保存）
        
        用于任务完成回调，实现断点续传能力
        
        Args:
            task_id: 任务ID
            task_result: 任务执行结果 {job_id: result}
            context: 执行上下文，可能包含 dry_run 标志
        """
        # 检查是否已经保存过（避免重复保存）
        if task_id in self._saved_tasks:
            return
        
        context = context or {}
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            return
        
        if not self.data_manager:
            logger.warning(f"[增量保存] data_manager 未设置，无法保存任务 {task_id}")
            return
        
        # 检查 _generated_tasks 是否已设置
        if not hasattr(self, '_generated_tasks') or not self._generated_tasks:
            logger.warning(f"[增量保存] _generated_tasks 未设置，无法处理任务 {task_id}")
            return
        
        try:
            # 处理单个任务的结果
            # task_result 格式：{job_id: result}
            # 需要转换为 _process_task_results 期望的格式：{task_id: {job_id: result}}
            task_results = {task_id: task_result}
            stock_data_map = self._process_task_results(task_results)
            
            # 保存该任务对应的股票数据
            for stock_id, records in stock_data_map.items():
                if not records:
                    continue
                
                try:
                    # 直接调用 data_manager 的 service 方法保存数据
                    stock_service = self.data_manager.get_data_service('stock_related.stock')
                    if stock_service:
                        count = stock_service.save_klines(records)
                        logger.info(f"✅ [增量保存] 股票 {stock_id} K 线数据，共 {count} 条记录（包含所有周期）")
                    else:
                        logger.warning(f"未找到 stock service，无法保存股票 {stock_id} K 线数据")
                except Exception as e:
                    logger.error(f"❌ [增量保存] 股票 {stock_id} K 线数据失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # 继续处理其他股票，不中断整个流程
            
            # 标记为已保存
            self._saved_tasks.add(task_id)
            
        except Exception as e:
            logger.error(f"❌ [增量保存] 任务 {task_id} 保存失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def after_execute(
        self, 
        task_results: Dict[str, Dict[str, Any]], 
        context: Dict[str, Any]
    ):
        """
        执行后的钩子：按股票分组保存数据
        
        策略：
        - 只保存尚未通过增量保存机制保存的任务（避免重复保存）
        - 如果所有任务都已通过增量保存，这里只做统计
        
        Args:
            task_results: Task 执行结果
            context: 执行上下文，可能包含 dry_run 标志
        """
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info(f"🧪 干运行模式：跳过数据保存（共 {len(self._generated_tasks)} 个 task）")
            return
        
        if not self.data_manager:
            logger.warning(f"{self.data_source} Handler 未设置 data_manager，无法保存数据")
            return
        
        # 找出尚未保存的任务（增量保存可能因为中断而未完成所有任务）
        unsaved_tasks = {task_id: result for task_id, result in task_results.items() 
                        if task_id not in self._saved_tasks}
        
        if not unsaved_tasks:
            # 所有任务都已通过增量保存完成
            logger.info(f"✅ K 线数据保存完成（所有任务已通过增量保存完成）")
            return
        
        # 处理未保存的任务结果
        stock_data_map = self._process_task_results(unsaved_tasks)
        
        # 按股票分组保存数据
        total_saved = 0
        for stock_id, records in stock_data_map.items():
            if not records:
                continue
            
            try:
                # 直接调用 data_manager 的 service 方法保存数据
                stock_service = self.data_manager.get_data_service('stock_related.stock')
                if stock_service:
                    count = stock_service.save_klines(records)
                    total_saved += count
                else:
                    logger.warning(f"未找到 stock service，无法保存股票 {stock_id} K 线数据")
            except Exception as e:
                logger.error(f"❌ 保存股票 {stock_id} K 线数据失败: {e}")
                # 继续处理其他股票，不中断整个流程
        
        if total_saved > 0:
            logger.info(f"✅ K 线数据保存完成，共 {len(stock_data_map)} 只股票，{total_saved} 条记录（包含所有周期）")
        else:
            logger.warning(f"⚠️ K 线数据没有可保存的记录")
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据
        
        注意：由于数据保存已经在 after_execute 中完成，这个方法主要用于返回标准化后的数据
        使用 _process_task_results 处理数据，然后展平所有记录返回
        """
        # 处理 Task 结果，获取按股票分组的记录
        stock_data_map = self._process_task_results(raw_data)
        
        # 展平所有记录
        all_records = []
        for records in stock_data_map.values():
            all_records.extend(records)
        
        logger.info(f"✅ K 线数据处理完成，共 {len(all_records)} 条记录（包含所有周期）")
        
        return {
            "data": all_records
        }
    
    def _merge_kline_and_basic(self, kline_df: pd.DataFrame, basic_df: pd.DataFrame, stock_id: str, term: str = None) -> pd.DataFrame:
        """
        合并 K 线和 daily_basic 数据，并处理缺失值
        
        Args:
            kline_df: K 线数据（已映射为 DB 字段）
            basic_df: daily_basic 数据（已映射为 DB 字段）
            stock_id: 股票代码
        
        Returns:
            合并后的 DataFrame
        """
        if kline_df.empty:
            return None
        
        # 字段映射（K 线数据）
        kline_mapped = self._map_kline_fields(kline_df, stock_id)
        
        # 字段映射（daily_basic 数据）
        # 注意：daily_basic 中有 close 字段，但 K-line 数据中也有 close 字段
        # 我们需要使用 K-line 的 close（更准确），所以从 basic_mapped 中移除 close
        basic_mapped = self._map_basic_fields(basic_df, stock_id) if not basic_df.empty else pd.DataFrame()
        
        # 移除 basic_mapped 中的 close 字段（使用 K-line 的 close 更准确）
        if not basic_mapped.empty and 'close' in basic_mapped.columns:
            basic_mapped = basic_mapped.drop(columns=['close'])
        
        # 合并数据
        if basic_mapped.empty:
            # daily_basic 失败，不保存数据，下次重试
            term_str = term or (hasattr(self, 'term') and self.term) or "unknown"
            logger.warning(f"⚠️  [{stock_id}] [{term_str}] daily_basic 数据为空，跳过保存，等待下次重试")
            return None
        
        # LEFT JOIN 合并（保留所有 K 线数据）
        merged = pd.merge(
            kline_mapped, 
            basic_mapped, 
            on=['id', 'date'], 
            how='left', 
            suffixes=('', '_basic')
        )
        
        # 前向填充缺失值
        # 注意：只在有数据的范围内填充，不应该跨数据范围填充
        # 例如：如果K线数据从2008年开始，但PE、PB从2020年才开始有，
        # 那么2008-2019年的PE、PB应该保持为NULL，不应该用2020年的数据填充
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
            # 对于 basic_mapped 日期范围之前的数据，保持为 NULL
            for col in basic_columns:
                if col in merged.columns:
                    # 只在 basic_mapped 日期范围内使用 ffill
                    mask = (merged['date'] >= basic_min_date) & (merged['date'] <= basic_max_date)
                    if mask.any():
                        # 在有数据的范围内使用 ffill
                        merged.loc[mask, col] = merged.loc[mask, col].ffill()
                        # 如果首行仍为空（在数据范围内），用 basic 的首个非 NaN 值填充
                        if basic_mapped[col].notna().any():
                            first_valid = basic_mapped[col].dropna().iloc[0]
                            merged.loc[mask, col] = merged.loc[mask, col].fillna(first_valid)
                    # 对于填充后仍然为 NaN 的字段，使用默认值 0（因为 schema 要求 NOT NULL）
                    # 注意：这些字段在 schema 中是 isRequired: true，不允许 NULL
                    if merged[col].isna().any():
                        merged[col] = merged[col].fillna(0.0)
                    # 对于 basic_mapped 日期范围之前的数据，使用默认值 0（因为 schema 要求 NOT NULL）
                    before_mask = merged['date'] < basic_min_date
                    if before_mask.any():
                        merged.loc[before_mask, col] = 0.0
        else:
            # 如果没有 basic 数据，所有 basic 字段使用默认值 0（因为 schema 要求 NOT NULL）
            for col in basic_columns:
                if col in merged.columns:
                    merged[col] = 0.0
        
        # 添加 term 字段
        if term:
            merged['term'] = term
        elif hasattr(self, 'term') and self.term:
            merged['term'] = self.term
        else:
            raise ValueError("无法确定 term，请传入 term 参数")
        
        # 清理数据：移除带 _basic 后缀的列（这些是合并时产生的重复列）
        columns_to_drop = [col for col in merged.columns if col.endswith('_basic')]
        if columns_to_drop:
            merged = merged.drop(columns=columns_to_drop)
        
        # 处理 NaN 值：将 NaN 转换为 None（MySQL 不支持 NaN）
        # 对所有列进行处理，确保没有 NaN 值
        for col in merged.columns:
            # 将 NaN 转换为 None（对所有类型都处理）
            merged[col] = merged[col].where(pd.notna(merged[col]), None)
        
        return merged
    
    def _map_kline_fields(self, df: pd.DataFrame, stock_id: str) -> pd.DataFrame:
        """
        映射 K 线字段（根据 legacy config）
        """
        if df.empty:
            return pd.DataFrame()
        
        # 字段映射（根据 legacy config）
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
        映射 daily_basic 字段（根据 legacy config）
        """
        if df.empty:
            return pd.DataFrame()
        
        # 字段映射（根据 legacy config）
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
                # 转换为数值类型，如果转换失败或为 NaN，使用默认值 0.0（因为 schema 要求 NOT NULL）
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce').fillna(0.0)
        
        for col in int_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce').fillna(0).astype(int)
        
        return mapped_df
