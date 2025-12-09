"""
K线数据 Handler 基类

从 Tushare 获取股票 K 线数据（日线/周线/月线）
每个周期需要合并 K 线数据和 daily_basic 基本面数据

说明：
- daily/weekly/monthly API 只返回价格和成交量数据（open, high, low, close, volume, amount）
- daily_basic API 返回基本面指标（PE、PB、换手率、市值等）
- 需要合并两个 API 的数据才能得到完整的 K 线数据
"""
from typing import List, Dict, Any
from loguru import logger
import pandas as pd

from app.data_source.data_source_handler import BaseDataSourceHandler
from app.data_source.api_job import DataSourceTask, ApiJob
from utils.date.date_utils import DateUtils


class BaseKlineHandler(BaseDataSourceHandler):
    """
    K线数据 Handler 基类
    
    共同逻辑：
    - 需要合并 K 线数据和 daily_basic 数据
    - 需要查询数据库获取每个股票的最新日期
    - 需要处理缺失值（前向填充）
    """
    
    # 子类需要定义
    term: str = None  # "daily" | "weekly" | "monthly"
    kline_method: str = None  # Provider 方法名，如 "get_daily_kline"
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params, data_manager)
        if not self.term or not self.kline_method:
            raise ValueError(f"{self.__class__.__name__} 必须定义 term 和 kline_method")
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        1. 获取股票列表
        2. 查询数据库获取每个股票的最新日期
        3. 计算每个股票需要更新的日期范围
        """
        context = context or {}
        
        # 获取股票列表
        if "stock_list" not in context:
            # 从依赖的 stock_list data source 获取，或从 data_manager 查询
            if self.data_manager:
                try:
                    # TODO: 从 data_manager 查询股票列表
                    logger.debug("从 data_manager 查询股票列表（待实现）")
                except Exception as e:
                    logger.warning(f"查询股票列表失败: {e}")
            
            # 如果没有，使用空列表（后续会报错）
            context["stock_list"] = []
        
        # 获取结束日期（通常是 latest_market_open_day - 1）
        if "end_date" not in context:
            # 默认使用当前日期
            context["end_date"] = DateUtils.get_current_date_str()
        
        # 查询数据库获取每个股票的最新日期
        if self.data_manager and context.get("stock_list"):
            try:
                # TODO: 查询数据库获取每个股票的最新日期
                # 这里需要实现查询逻辑
                logger.debug("从数据库查询每个股票的最新日期（待实现）")
            except Exception as e:
                logger.warning(f"查询数据库失败: {e}")
    
    async def fetch(self, context: Dict[str, Any] = None) -> List['DataSourceTask']:
        """
        生成获取 K 线数据的 Tasks
        
        逻辑：
        1. 从 context 获取股票列表和日期范围
        2. 为每个股票创建一个 Task
        3. 每个 Task 包含两个 ApiJob：
           - K 线 API（daily/weekly/monthly）- 获取价格和成交量数据
           - daily_basic API - 获取基本面指标（PE、PB、换手率、市值等）
        """
        context = context or {}
        
        stock_list = context.get("stock_list", [])
        end_date = context.get("end_date")
        
        if not stock_list:
            logger.warning("股票列表为空，无法获取 K 线数据")
            return []
        
        if not end_date:
            raise ValueError(f"{self.__class__.__name__} 需要 end_date 参数")
        
        logger.debug(f"为 {len(stock_list)} 只股票生成 {self.term} K 线数据获取任务，截止日期: {end_date}")
        
        tasks = []
        for stock in stock_list:
            stock_id = stock.get("ts_code") or stock.get("id")
            stock_name = stock.get("name", "")
            
            if not stock_id:
                continue
            
            # 计算该股票的 start_date
            # 从 context 中获取该股票的最新日期，如果没有则使用默认日期
            stock_latest_date = context.get("stock_latest_dates", {}).get(stock_id)
            
            if stock_latest_date:
                # 已有数据，从最新日期 + 1 天开始
                start_date = DateUtils.get_date_after_days(stock_latest_date, 1)
            else:
                # 新股票，使用默认开始日期（如 2020-01-01）
                from app.conf.conf import data_default_start_date
                start_date = data_default_start_date
            
            # 创建 Task：包含两个 ApiJob（K 线 + daily_basic）
            task_id = f"{self.data_source}_{stock_id}_{self.term}"
            
            # ApiJob 1: K 线数据（价格和成交量）
            kline_job = ApiJob(
                provider_name="tushare",
                method=self.kline_method,
                params={
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                api_name=self.kline_method,
            )
            
            # ApiJob 2: daily_basic 数据（基本面指标：PE、PB、换手率、市值等）
            # 注意：即使是周线/月线，也需要 daily_basic 来获取对应日期的基本面指标
            basic_job = ApiJob(
                provider_name="tushare",
                method="get_daily_basic",
                params={
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                api_name="get_daily_basic",
            )
            
            task = DataSourceTask(
                task_id=task_id,
                api_jobs=[kline_job, basic_job],
                description=f"获取 {stock_name} ({stock_id}) {self.term} K 线数据",
            )
            
            tasks.append(task)
        
        # 保存生成的 tasks（用于 normalize 中查找）
        self._generated_tasks = tasks
        
        logger.info(f"✅ 生成了 {len(tasks)} 个 {self.term} K 线数据获取任务")
        
        return tasks
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据
        
        合并 K 线数据和 daily_basic 数据，进行字段映射，处理缺失值
        """
        all_records = []
        
        # 遍历所有 Task 的结果
        for task in self._generated_tasks:
            task_id = task.task_id
            stock_id = task.api_jobs[0].params.get("ts_code")
            
            if task_id not in raw_data:
                logger.warning(f"Task {task_id} 没有执行结果")
                continue
            
            task_results = raw_data[task_id]
            
            # 获取两个 ApiJob 的结果
            kline_job_id = f"{task_id}_job_0"  # 第一个 job 是 K 线
            basic_job_id = f"{task_id}_job_1"  # 第二个 job 是 daily_basic
            
            kline_df = task_results.get(kline_job_id)
            basic_df = task_results.get(basic_job_id)
            
            if kline_df is None or (isinstance(kline_df, pd.DataFrame) and kline_df.empty):
                logger.debug(f"股票 {stock_id} {self.term} K 线数据为空")
                continue
            
            # 转换为 DataFrame
            if not isinstance(kline_df, pd.DataFrame):
                kline_df = pd.DataFrame(kline_df) if kline_df else pd.DataFrame()
            
            if not isinstance(basic_df, pd.DataFrame):
                basic_df = pd.DataFrame(basic_df) if basic_df else pd.DataFrame()
            
            # 合并数据
            merged_df = self._merge_kline_and_basic(kline_df, basic_df, stock_id)
            
            if merged_df is not None and not merged_df.empty:
                # 转换为字典列表
                records = merged_df.to_dict('records')
                all_records.extend(records)
        
        logger.info(f"✅ {self.term} K 线数据处理完成，共 {len(all_records)} 条记录")
        
        return {
            "data": all_records
        }
    
    def _merge_kline_and_basic(self, kline_df: pd.DataFrame, basic_df: pd.DataFrame, stock_id: str) -> pd.DataFrame:
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
        basic_mapped = self._map_basic_fields(basic_df, stock_id) if not basic_df.empty else pd.DataFrame()
        
        # 合并数据
        if basic_mapped.empty:
            # daily_basic 失败，不保存数据，下次重试
            logger.warning(f"⚠️  [{stock_id}] [{self.term}] daily_basic 数据为空，跳过保存，等待下次重试")
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
        basic_columns = [
            'turnover_rate', 'free_turnover_rate', 'volume_ratio',
            'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm',
            'dv_ratio', 'dv_ttm',
            'total_share', 'float_share', 'free_share',
            'total_market_value', 'circ_market_value'
        ]
        
        # 按日期排序后前向填充
        merged = merged.sort_values('date')
        for col in basic_columns:
            if col in merged.columns:
                merged[col] = merged[col].ffill()
                # 如果首行仍为空，用 basic 的首个非 NaN 值填充
                if basic_mapped[col].notna().any():
                    first_valid = basic_mapped[col].dropna().iloc[0]
                    merged[col] = merged[col].fillna(first_valid)
        
        # 添加 term 字段
        merged['term'] = self.term
        
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
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce')
        
        for col in int_cols:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce').fillna(0).astype(int)
        
        return mapped_df

