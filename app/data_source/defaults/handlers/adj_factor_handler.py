"""
复权因子 Handler

从 Tushare 和 AKShare 获取数据，计算复权因子

业务逻辑：
1. 从 Tushare adj_factor API 获取复权事件日期
2. 从 Tushare daily_kline API 获取原始收盘价
3. 从 AKShare qfq_kline API 获取前复权收盘价
4. 计算：qfq_factor = qfq_close_price / raw_close_price
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
import pandas as pd

from app.data_source.data_source_handler import BaseDataSourceHandler
from app.data_source.api_job import DataSourceTask, ApiJob
from utils.date.date_utils import DateUtils


class AdjFactorHandler(BaseDataSourceHandler):
    """
    复权因子 Handler
    
    从 Tushare 和 AKShare 获取数据，计算复权因子。
    
    特点：
    - 需要多个 API 调用（Tushare adj_factor + Tushare daily_kline + AKShare qfq_kline）
    - 增量更新（incremental）
    - 需要按股票逐个获取（每个股票一个 Task）
    - 需要计算日期范围（基于数据库最新记录）
    """
    
    # 类属性（必须定义）
    data_source = "adj_factor"
    renew_type = "incremental"  # 增量更新
    description = "获取复权因子数据"
    dependencies = ["stock_list", "daily_kline"]  # 依赖股票列表和日线数据
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)
        # 默认起始日期（从 legacy 代码中获取）
        self.default_start_date = "20100101"
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        查询数据库获取最新复权因子日期，计算需要更新的日期范围
        获取股票列表
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
        else:
            # 从 data_manager 查询数据库获取最新复权因子日期
            if self.data_manager:
                try:
                    # TODO: 查询数据库获取每个股票的最新复权因子日期
                    logger.debug("从数据库查询最新复权因子日期（待实现）")
                except Exception as e:
                    logger.warning(f"查询数据库失败，使用默认日期范围: {e}")
            
            # 如果没有数据库或查询失败，使用默认范围
            if "start_date" not in context:
                context["start_date"] = self.default_start_date
            if "end_date" not in context:
                # 使用当前日期
                context["end_date"] = DateUtils.get_current_date_str()
                logger.debug(f"使用默认日期范围: {context['start_date']} 至 {context['end_date']}")
        
        # 获取股票列表（从依赖或 context）
        if "stock_list" not in context:
            # TODO: 从依赖的 stock_list data source 获取
            # 或者从 data_manager 查询数据库
            logger.warning("股票列表未提供，将无法获取复权因子")
            context["stock_list"] = []
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """
        生成获取复权因子数据的 Tasks
        
        逻辑：
        1. 从 context 获取股票列表和日期范围
        2. 为每个股票创建一个 Task（包含 3 个 ApiJob）：
           - Tushare adj_factor API - 获取复权事件日期
           - Tushare daily_kline API - 获取原始收盘价
           - AKShare qfq_kline API - 获取前复权收盘价
        """
        context = context or {}
        
        stock_list = context.get("stock_list", [])
        start_date = context.get("start_date")
        end_date = context.get("end_date")
        
        if not stock_list:
            logger.warning("股票列表为空，无法获取复权因子")
            return []
        
        if not start_date or not end_date:
            raise ValueError("Adj Factor Handler 需要 start_date 和 end_date 参数")
        
        logger.debug(f"为 {len(stock_list)} 只股票生成复权因子获取任务: {start_date} 至 {end_date}")
        
        # 为每个股票创建一个 Task
        tasks = []
        for stock in stock_list:
            stock_id = stock.get('id') if isinstance(stock, dict) else stock
            if not stock_id:
                continue
            
            # 提取股票代码（去掉市场后缀，用于 AKShare）
            # Tushare 格式：000001.SZ -> AKShare 格式：000001
            akshare_symbol = stock_id.split('.')[0] if '.' in stock_id else stock_id
            
            # 创建 3 个 ApiJob
            # 1. Tushare adj_factor - 获取复权事件日期
            adj_factor_job = ApiJob(
                provider_name="tushare",
                method="get_adj_factor",
                params={
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                job_id=f"adj_factor_{stock_id}",
            )
            
            # 2. Tushare daily_kline - 获取原始收盘价
            daily_kline_job = ApiJob(
                provider_name="tushare",
                method="get_daily_kline",
                params={
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                job_id=f"daily_kline_{stock_id}",
            )
            
            # 3. AKShare qfq_kline - 获取前复权收盘价
            qfq_kline_job = ApiJob(
                provider_name="akshare",
                method="get_qfq_kline",
                params={
                    "symbol": akshare_symbol,
                    "period": "daily",
                    "start_date": start_date,
                    "end_date": end_date,
                    "adjust": "qfq",
                },
                job_id=f"qfq_kline_{stock_id}",
            )
            
            # 创建 Task（包含 3 个 ApiJob）
            task = DataSourceTask(
                task_id=f"adj_factor_{stock_id}",
                api_jobs=[adj_factor_job, daily_kline_job, qfq_kline_job],
                description=f"获取 {stock_id} 的复权因子",
            )
            
            tasks.append(task)
        
        logger.info(f"✅ 生成了 {len(tasks)} 个复权因子获取任务")
        
        return tasks
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 3 个 API 的结果中计算复权因子：
        1. 从 Tushare adj_factor 获取复权事件日期
        2. 从 Tushare daily_kline 获取原始收盘价
        3. 从 AKShare qfq_kline 获取前复权收盘价
        4. 计算：qfq_factor = qfq_close_price / raw_close_price
        """
        formatted = []
        
        # task_results 的结构：{task_id: {job_id: result}}
        for task_id, task_result in task_results.items():
            if not task_result:
                continue
            
            # 提取股票代码
            stock_id = task_id.replace("adj_factor_", "")
            
            # 获取 3 个 API 的结果
            adj_factor_df = task_result.get(f"adj_factor_{stock_id}")
            daily_kline_df = task_result.get(f"daily_kline_{stock_id}")
            qfq_kline_df = task_result.get(f"qfq_kline_{stock_id}")
            
            # 检查数据是否完整
            if adj_factor_df is None or adj_factor_df.empty:
                logger.warning(f"{stock_id} 的复权因子数据为空，跳过")
                continue
            
            if daily_kline_df is None or daily_kline_df.empty:
                logger.warning(f"{stock_id} 的原始K线数据为空，跳过")
                continue
            
            if qfq_kline_df is None or qfq_kline_df.empty:
                logger.warning(f"{stock_id} 的前复权K线数据为空，跳过")
                continue
            
            # 提取复权事件日期（从 adj_factor 中找出因子发生变化的日期）
            factor_changing_dates = self._get_factor_changing_dates(adj_factor_df)
            
            if not factor_changing_dates:
                logger.debug(f"{stock_id} 没有复权事件，跳过")
                continue
            
            # 构建原始收盘价字典（从 Tushare daily_kline）
            raw_close_prices = {}
            for _, row in daily_kline_df.iterrows():
                trade_date = str(row.get('trade_date', ''))
                close_price = float(row.get('close', 0))
                if trade_date and close_price > 0:
                    raw_close_prices[trade_date] = close_price
            
            # 构建前复权收盘价字典（从 AKShare qfq_kline）
            qfq_close_prices = {}
            for _, row in qfq_kline_df.iterrows():
                # AKShare 返回的日期格式可能是 "2024-01-01" 或 "20240101"
                date_str = str(row.get('日期', ''))
                if not date_str:
                    continue
                
                # 转换为 YYYYMMDD 格式
                trade_date = DateUtils.normalize_date(date_str)
                if not trade_date:
                    continue
                
                close_price = float(row.get('收盘', 0))
                if close_price > 0:
                    qfq_close_prices[trade_date] = close_price
            
            # 计算复权因子
            for date in factor_changing_dates:
                raw_close = raw_close_prices.get(date)
                qfq_close = qfq_close_prices.get(date)
                
                if raw_close is None or raw_close == 0:
                    logger.warning(f"{stock_id} 在 {date} 原始收盘价为0或不存在，跳过该日因子计算")
                    continue
                
                if qfq_close is None or qfq_close == 0:
                    logger.warning(f"{stock_id} 在 {date} 前复权收盘价为0或不存在，跳过该日因子计算")
                    continue
                
                # 计算前复权因子
                qfq_factor = qfq_close / raw_close
                
                formatted.append({
                    "id": stock_id,
                    "date": date,
                    "qfq": qfq_factor,
                    "hfq": 0.0,  # 后复权因子暂时设为 0（legacy 代码中也是这样的）
                })
        
        logger.info(f"✅ 复权因子数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }
    
    def _get_factor_changing_dates(self, adj_factor_df: pd.DataFrame) -> List[str]:
        """
        从 Tushare adj_factor 数据中提取复权事件日期（因子发生变化的日期）
        
        逻辑：
        1. 按日期排序（从旧到新）
        2. 找出因子发生变化的日期
        """
        if adj_factor_df is None or adj_factor_df.empty:
            return []
        
        # 按日期排序（从旧到新）
        adj_factor_df = adj_factor_df.sort_values('trade_date', ascending=True)
        
        changing_dates = []
        prev_factor = None
        
        for _, row in adj_factor_df.iterrows():
            current_factor = float(row.get('adj_factor', 0))
            trade_date = str(row.get('trade_date', ''))
            
            if not trade_date:
                continue
            
            # 只有当因子真正发生变化时才记录日期
            if prev_factor is not None and current_factor != prev_factor:
                changing_dates.append(trade_date)
            
            prev_factor = current_factor
        
        return changing_dates

