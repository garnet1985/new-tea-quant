"""
股指指标 Handler

从 Tushare 获取指数 K 线数据（日线/周线/月线）
以指数为单位处理，每个指数创建一个 Task，包含 3 个 API Job：
1. get_index_daily - 指数日线数据
2. get_index_weekly - 指数周线数据
3. get_index_monthly - 指数月线数据

说明：
- 指数K线数据不包含基本面指标（daily_basic），所以只需要3个API调用
- 支持多个指数（上证指数、沪深300、科创50、深证成指、创业板指等）
"""
from typing import List, Dict, Any
from loguru import logger
import pandas as pd

from core.modules.data_source.data_source_handler import BaseDataSourceHandler
from core.modules.data_source.api_job import DataSourceTask, ApiJob
from core.utils.date.date_utils import DateUtils


class StockIndexIndicatorHandler(BaseDataSourceHandler):
    """
    股指指标 Handler
    
    以指数为单位处理，每个指数创建一个 Task，包含 3 个 API Job：
    1. get_index_daily - 指数日线数据
    2. get_index_weekly - 指数周线数据
    3. get_index_monthly - 指数月线数据
    """
    data_source = "stock_index_indicator"
    description = "获取股指指标数据（指数K线），支持 daily/weekly/monthly 周期"
    dependencies = []
    requires_date_range = True
    
    # 周期映射表
    TERM_MAPPING = {
        "daily": {
            "kline_method": "get_index_daily",
            "description": "指数日线数据"
        },
        "weekly": {
            "kline_method": "get_index_weekly",
            "description": "指数周线数据"
        },
        "monthly": {
            "kline_method": "get_index_monthly",
            "description": "指数月线数据"
        }
    }
    
    def __init__(self, schema, data_manager=None, definition=None):
        """初始化股指指标 Handler"""
        super().__init__(schema, data_manager, definition)
        # 默认指数列表
        self.index_list = self.get_param('index_list', [
            {'id': '000001.SH', 'name': '上证指数'},
            {'id': '000300.SH', 'name': '沪深300'},
            {'id': '000688.SH', 'name': '科创50'},
            {'id': '399001.SZ', 'name': '深证成指'},
            {'id': '399006.SZ', 'name': '创业板指'},
        ])
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        1. 获取最新交易日，并计算每个周期的结束日期
        2. 查询数据库获取每个指数在 3 个周期（daily/weekly/monthly）的最新日期
        """
        if context is None:
            context = {}
        
        # 1. 获取最新交易日，并计算每个周期的结束日期
        # 优先从 context 读取（由 renew_data() 统一获取并注入），避免多次获取导致数据不一致
        latest_trading_date = context.get("latest_completed_trading_date")
        if not latest_trading_date and self.data_manager:
            # 兜底：如果 context 中没有，才自己获取（不应该发生，但保留兜底逻辑）
            logger.warning("StockIndexIndicatorHandler.before_fetch: context 中未找到 latest_completed_trading_date，回退获取")
            try:
                latest_trading_date = self.data_manager.service.calendar.get_latest_completed_trading_date()
            except Exception as e:
                logger.warning(f"获取最新交易日失败: {e}")
                latest_trading_date = DateUtils.get_current_date_str()
        
        if latest_trading_date:
            # 计算每个周期的结束日期
            end_dates = {
                "daily": DateUtils.get_date_before_days(latest_trading_date, 1),  # 日线：前一个交易日
                "weekly": DateUtils.get_previous_week_end(latest_trading_date),  # 周线：上个完整周
                "monthly": DateUtils.get_previous_month_end(latest_trading_date),  # 月线：上个完整月
            }
            context["end_dates"] = end_dates
        else:
            # 如果仍然没有，使用当前日期作为兜底
            latest_trading_date = DateUtils.get_current_date_str()
            context["end_dates"] = {
                "daily": latest_trading_date,
                "weekly": latest_trading_date,
                "monthly": latest_trading_date,
            }
        
        # 2. 查询数据库获取每个指数在 3 个周期的最新日期（批量查询）
        index_latest_dates_by_term = {}  # {index_id: {term: latest_date}}
        if self.data_manager:
            try:
                # 构建指数 ID 列表（用于过滤）
                index_ids = [index_info['id'] for index_info in self.index_list]
                
                # 使用 service 批量查询：一次性获取所有指数的所有周期的最新记录
                all_index_latest_dates = self.data_manager.index.load_latest_indicators_by_term(index_ids=index_ids)
                # 只保留配置中的指数
                index_latest_dates_by_term = all_index_latest_dates
            except Exception as e:
                logger.warning(f"查询指数历史记录失败: {e}")
        
        context["index_latest_dates_by_term"] = index_latest_dates_by_term
        
        return context
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """生成获取股指指标数据的 Tasks"""
        context = context or {}
        
        end_dates = context.get("end_dates", {})
        index_latest_dates_by_term = context.get("index_latest_dates_by_term", {})
        
        tasks = []
        
        for index_info in self.index_list:
            index_id = index_info['id']
            index_name = index_info.get('name', index_id)
            
            # 为每个周期创建 ApiJob
            api_jobs = []
            
            for term, term_config in self.TERM_MAPPING.items():
                end_date = end_dates.get(term)
                if not end_date:
                    continue
                
                # 计算开始日期
                latest_dates = index_latest_dates_by_term.get(index_id, {})
                latest_date = latest_dates.get(term)
                
                if latest_date:
                    # 有历史记录，从下一天开始
                    start_date = DateUtils.get_date_after_days(latest_date, 1)
                else:
                    # 无历史记录，使用默认起始日期
                    from core.infra.project_context import ConfigManager
                    start_date = ConfigManager.get_default_start_date()

                # 如果开始日期大于结束日期，跳过
                if start_date > end_date:
                    continue
                
                # 创建 ApiJob
                kline_method = term_config["kline_method"]
                api_job = ApiJob(
                    provider_name="tushare",
                    method=kline_method,
                    params={
                        "ts_code": index_id,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                    job_id=f"{index_id}_{term}",
                    api_name=kline_method
                )
                api_jobs.append(api_job)
            
            if not api_jobs:
                continue
            
            # 创建 Task
            task = DataSourceTask(
                task_id=f"index_indicator_{index_id}",
                api_jobs=api_jobs,
                description=f"获取 {index_name} ({index_id}) 的指数K线数据",
            )
            tasks.append(task)
        
        logger.info(f"✅ 生成了 {len(tasks)} 个指数K线数据获取任务")
        
        return tasks
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 3 个 API 的结果中处理数据，按指数和周期分组
        """
        formatted = []
        
        # task_results 的结构：{task_id: {job_id: result}}
        for task_id, task_result in task_results.items():
            if not task_id.startswith("index_indicator_"):
                continue
            
            index_id = task_id.replace("index_indicator_", "")
            
            # 处理每个周期的数据
            for term, term_config in self.TERM_MAPPING.items():
                job_id = f"{index_id}_{term}"
                kline_df = task_result.get(job_id)
                
                if kline_df is None or kline_df.empty:
                    continue
                
                # 处理数据
                for _, row in kline_df.iterrows():
                    trade_date = str(row.get('trade_date', ''))
                    if not trade_date:
                        continue
                    
                    # 统一日期格式为 YYYYMMDD
                    date_ymd = trade_date.replace('-', '') if '-' in trade_date else trade_date
                    
                    record = {
                        'id': index_id,
                        'term': term,
                        'date': date_ymd,
                        'open': float(row.get('open', 0)),
                        'close': float(row.get('close', 0)),
                        'highest': float(row.get('high', 0)),
                        'lowest': float(row.get('low', 0)),
                        'pre_close': float(row.get('pre_close', 0)),
                        'price_change_delta': float(row.get('change', 0)),
                        'price_change_rate_delta': float(row.get('pct_chg', 0)),
                        'volume': int(row.get('vol', 0)),
                        'amount': float(row.get('amount', 0)),
                    }
                    
                    formatted.append(record)
        
        logger.info(f"✅ 股指指标数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }

    async def after_normalize(self, normalized_data: Dict[str, Any], context: Dict[str, Any] = None):
        """
        标准化后处理：保存股指指标数据到数据库
        """
        context = context or {}

        # 当前框架调用 after_normalize 时没有把 context 传进来，
        # 这里的 dry_run 暂时不会生效，但保留逻辑以便后续框架调整。
        dry_run = context.get("dry_run", False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过股指指标数据保存")
            return

        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法保存股指指标数据")
            return

        data_list = normalized_data.get("data") if isinstance(normalized_data, dict) else None
        if not data_list:
            logger.debug("股指指标数据为空，无需保存")
            return

        try:
            from core.infra.db.helpers.db_helpers import DBHelper
            data_list = DBHelper.clean_nan_in_list(data_list, default=0.0)

            # 使用 service 保存数据
            count = self.data_manager.index.save_indicator(data_list)
            logger.info(f"✅ 股指指标数据保存完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存股指指标数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

