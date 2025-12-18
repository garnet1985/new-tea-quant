"""
复权因子事件 Handler 的辅助函数集合

将复杂的业务逻辑拆分为语义化的静态方法，便于测试和维护。
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import pandas as pd
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.data_source.providers.provider_instance_pool import ProviderInstancePool
from utils.date.date_utils import DateUtils


class AdjFactorEventHandlerHelper:
    """复权因子事件处理器的辅助函数集合"""
    
    # ========== 状态判断类 ==========
    
    @staticmethod
    def is_table_empty(model) -> bool:
        """判断 adj_factor_event 表是否为空"""
        return model.is_table_empty()
    
    @staticmethod
    def is_csv_usable(model) -> bool:
        """
        判断当前是否存在"可用"的 CSV 快照
        
        可用的定义：
        - 能找到最新 CSV 文件
        - 文件存在且可读取
        - 至少包含 id / event_date / factor / qfq_diff 四个字段
        """
        import os
        import pandas as pd
        
        latest_csv = model.get_latest_csv_file()
        if not latest_csv:
            return False
        if not os.path.exists(latest_csv):
            return False
        
        try:
            df = pd.read_csv(latest_csv, nrows=10)
            required_cols = {'id', 'event_date', 'factor', 'qfq_diff'}
            missing = required_cols - set(df.columns)
            if missing:
                logger.warning(f"CSV 文件缺少必需列 {missing}，视为不可用: {latest_csv}")
                return False
            return True
        except Exception as e:
            logger.warning(f"读取/校验 CSV 失败，视为不可用: {latest_csv}, error={e}")
            return False
    
    @staticmethod
    def get_stocks_with_existing_factors(model) -> List[str]:
        """返回当前 adj_factor_event 表中已存在复权因子事件的股票ID列表"""
        return model.load_all_stock_ids()
    
    @staticmethod
    def compute_coverage_ratio(existing_ids: List[str], all_ids: List[str]) -> float:
        """
        计算 adj_factor_event 表对指定股票 universe 的覆盖率
        
        Args:
            existing_ids: 在 adj_factor_event 中已经有记录的股票ID列表
            all_ids: 当前需要考虑的股票ID全集
        
        Returns:
            覆盖率（0.0-1.0）
        """
        if not all_ids:
            return 0.0
        existing_set = set(existing_ids)
        all_set = set(all_ids)
        covered = len(existing_set & all_set)
        return covered / len(all_set)
    
    # ========== 数据转换类 ==========
    
    @staticmethod
    def convert_to_eastmoney_secid(stock_id: str) -> str:
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
    
    # ========== 数据解析类 ==========
    
    @staticmethod
    def parse_eastmoney_qfq_price_map(eastmoney_result: Any) -> Dict[str, float]:
        """
        解析东方财富 API 返回的全量前复权价格，构建日期 -> QFQ 价格的映射
        
        Args:
            eastmoney_result: 东方财富 Provider 返回的 JSON 数据（dict）
        
        Returns:
            Dict[str, float]: 日期（YYYYMMDD格式） -> 前复权收盘价的映射
        """
        qfq_map = {}
        
        try:
            if not isinstance(eastmoney_result, dict):
                return qfq_map
            
            klines = eastmoney_result.get('data', {}).get('klines', [])
            if not klines:
                return qfq_map
            
            # klines 格式：["2024-12-15,11.46", "2024-12-14,11.45", ...]
            # 第一个字段是日期（YYYY-MM-DD），第二个字段是收盘价
            for kline_str in klines:
                parts = kline_str.split(',')
                if len(parts) >= 2:
                    date_str = parts[0]  # YYYY-MM-DD
                    close_price = float(parts[1])
                    
                    # 转换为 YYYYMMDD 格式
                    date_ymd = date_str.replace('-', '')
                    qfq_map[date_ymd] = close_price
            
        except Exception as e:
            logger.warning(f"解析东方财富 API 数据失败: {e}")
        
        return qfq_map
    
    @staticmethod
    def parse_eastmoney_qfq_price(eastmoney_result: Any, event_date_ymd: str) -> Optional[float]:
        """
        解析东方财富 API 返回的前复权价格（单日）
        
        Args:
            eastmoney_result: 东方财富 Provider 返回的 JSON 数据（dict）
            event_date_ymd: 日期（YYYYMMDD格式）
        
        Returns:
            前复权收盘价，如果解析失败返回 None
        """
        qfq_map = AdjFactorEventHandlerHelper.parse_eastmoney_qfq_price_map(eastmoney_result)
        return qfq_map.get(event_date_ymd)
    
    @staticmethod
    def build_raw_price_map(daily_kline_df: pd.DataFrame) -> Dict[str, float]:
        """
        从日线数据构建日期 -> 原始收盘价的映射
        
        Args:
            daily_kline_df: Tushare daily_kline API 返回的 DataFrame
        
        Returns:
            Dict[str, float]: 日期（YYYYMMDD格式） -> 原始收盘价的映射
        """
        raw_price_map = {}
        
        if daily_kline_df is None or daily_kline_df.empty:
            return raw_price_map
        
        daily_kline_df = daily_kline_df.sort_values('trade_date', ascending=True)
        for _, row in daily_kline_df.iterrows():
            trade_date = str(row.get('trade_date', ''))
            close_price = float(row.get('close', 0))
            if trade_date and close_price > 0:
                raw_price_map[trade_date] = close_price
        
        return raw_price_map
    
    # ========== 复权因子计算类 ==========
    
    @staticmethod
    def get_factor_changing_dates(adj_factor_df: pd.DataFrame) -> List[str]:
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
    
    @staticmethod
    def get_factor_for_date(adj_factor_df: pd.DataFrame, event_date_ymd: str, default_factor: float = 1.0) -> float:
        """
        获取指定日期的复权因子
        
        Args:
            adj_factor_df: Tushare adj_factor API 返回的 DataFrame
            event_date_ymd: 事件日期（YYYYMMDD格式）
            default_factor: 默认因子（如果找不到数据）
        
        Returns:
            float: 复权因子
        """
        if adj_factor_df is None or adj_factor_df.empty:
            return default_factor
        
        # 查找该事件日的复权因子
        event_row = adj_factor_df[adj_factor_df['trade_date'] == event_date_ymd]
        if not event_row.empty:
            return float(event_row.iloc[0]['adj_factor'])
        
        # 如果事件日不在复权因子数据中（如第一根日线），使用该日期之前最近的因子
        prev_rows = adj_factor_df[adj_factor_df['trade_date'] <= event_date_ymd]
        if not prev_rows.empty:
            return float(prev_rows.iloc[-1]['adj_factor'])
        
        # 如果该日期之前也没有数据，使用默认因子
        return default_factor
    
    @staticmethod
    def calculate_qfq_diff(raw_close: float, eastmoney_qfq: Optional[float]) -> float:
        """
        计算 qfq_diff = raw_price - EastMoney_QFQ
        
        Args:
            raw_close: Tushare 原始收盘价
            eastmoney_qfq: 东方财富前复权价格（如果为 None，返回 0.0）
        
        Returns:
            float: qfq_diff
        """
        if eastmoney_qfq is not None:
            return raw_close - eastmoney_qfq
        return 0.0
    
    # ========== 预筛选类 ==========
    
    @staticmethod
    def normalize_date_to_yyyymmdd(date_value: Any) -> str:
        """
        将日期值标准化为 YYYYMMDD 格式字符串
        
        Args:
            date_value: 可以是 datetime.date、YYYY-MM-DD 字符串、YYYYMMDD 字符串等
        
        Returns:
            str: YYYYMMDD 格式的日期字符串
        """
        if isinstance(date_value, date):
            return date_value.strftime('%Y%m%d')
        elif isinstance(date_value, str):
            if '-' in date_value:
                return DateUtils.yyyy_mm_dd_to_yyyymmdd(date_value)
            else:
                return date_value
        else:
            return str(date_value).replace('-', '')
    
    @staticmethod
    def check_stock_has_factor_changes(
        stock_id: str,
        stock_info: Dict[str, Any],
        end_date: str,
        tushare_provider
    ) -> Optional[Dict[str, Any]]:
        """
        检查单只股票在最近一段时间内是否有因子变化
        
        Args:
            stock_id: 股票代码
            stock_info: 股票信息（包含 latest_event_date, first_kline_date）
            end_date: 结束日期（YYYY-MM-DD 或 YYYYMMDD）
            tushare_provider: Tushare Provider 实例
        
        Returns:
            如果有变化，返回包含 stock_id 和 first_kline_date 的字典；否则返回 None
        """
        try:
            latest_event_date = stock_info.get('latest_event_date')
            first_kline_date = stock_info.get('first_kline_date')
            
            # 确定查询起始日期
            if latest_event_date:
                start_date = AdjFactorEventHandlerHelper.normalize_date_to_yyyymmdd(latest_event_date)
            elif first_kline_date:
                start_date = AdjFactorEventHandlerHelper.normalize_date_to_yyyymmdd(first_kline_date)
            else:
                start_date = "20080101"  # 默认起始日期
            
            end_date_ymd = AdjFactorEventHandlerHelper.normalize_date_to_yyyymmdd(end_date)
            
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
            
            # 只要在最近一段时间内发生过因子变化，就标记该股票需要"全量重算"
            changing_dates = AdjFactorEventHandlerHelper.get_factor_changing_dates(adj_factor_df)
            if changing_dates:
                return {
                    'stock_id': stock_id,
                    'first_kline_date': first_kline_date,
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"预筛选股票 {stock_id} 失败: {e}")
            return None
    
    @staticmethod
    def prefilter_stocks_with_changes(
        stock_ids: List[str],
        stock_info_map: Dict[str, Dict[str, Any]],
        end_date: str,
        max_workers: int = 10
    ) -> List[Dict[str, Any]]:
        """
        多线程预筛选：调用 Tushare adj_factor API，找出"需要全量重算"的股票
        
        Args:
            stock_ids: 需要检查的股票ID列表
            stock_info_map: 股票信息映射（stock_id -> {latest_event_date, first_kline_date}）
            end_date: 结束日期（YYYY-MM-DD 或 YYYYMMDD）
            max_workers: 最大线程数
        
        Returns:
            List[Dict]: 有变化的股票列表，每个元素包含：
                - stock_id: 股票代码
                - first_kline_date: 第一根K线日期（用于确定全量重算起点）
        """
        provider_pool = ProviderInstancePool()
        tushare_provider = provider_pool.get_provider('tushare')
        
        if not tushare_provider:
            logger.error("无法获取 Tushare Provider")
            return []
        
        stocks_with_changes = []
        
        def check_stock(stock_id: str) -> Optional[Dict[str, Any]]:
            stock_info = stock_info_map.get(stock_id, {})
            return AdjFactorEventHandlerHelper.check_stock_has_factor_changes(
                stock_id, stock_info, end_date, tushare_provider
            )
        
        # 多线程执行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
    
    # ========== 事件构建类 ==========
    
    @staticmethod
    def build_adj_factor_events(
        stock_id: str,
        adj_factor_df: pd.DataFrame,
        raw_price_map: Dict[str, float],
        eastmoney_qfq_map: Dict[str, float],
        first_kline_ymd: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        构建复权因子事件列表
        
        Args:
            stock_id: 股票代码
            adj_factor_df: Tushare adj_factor API 返回的 DataFrame
            raw_price_map: 日期 -> 原始收盘价的映射
            eastmoney_qfq_map: 日期 -> 东方财富前复权价格的映射
            first_kline_ymd: 第一根K线日期（YYYYMMDD格式）
        
        Returns:
            List[Dict]: 复权因子事件列表，每个元素包含：
                - id: 股票代码
                - event_date: 事件日期（YYYYMMDD格式）
                - factor: 复权因子
                - qfq_diff: qfq_diff
        """
        if adj_factor_df is None or adj_factor_df.empty:
            return []
        
        # 处理复权因子数据：按日期排序
        adj_factor_df = adj_factor_df.sort_values('trade_date', ascending=True)
        
        # 获取第一个复权因子（用于从未有复权事件的股票）
        first_factor = 1.0
        if not adj_factor_df.empty:
            first_row = adj_factor_df.iloc[0]
            first_factor = float(first_row.get('adj_factor', 1.0))
        
        # 计算所有复权事件日期（因子变化的日期）
        changing_dates = AdjFactorEventHandlerHelper.get_factor_changing_dates(adj_factor_df)
        
        # 确保第一根日线日期作为一个事件点
        if first_kline_ymd and first_kline_ymd not in changing_dates:
            changing_dates.insert(0, first_kline_ymd)
        
        # 如果从未有复权事件（changing_dates 为空），但存在第一根K线，确保至少保存一条记录
        if not changing_dates:
            if first_kline_ymd:
                changing_dates = [first_kline_ymd]
            else:
                return []
        
        # 为每个事件日期计算 qfq_diff 并构建事件记录
        events = []
        
        for event_date_ymd in changing_dates:
            # 获取该事件日的复权因子
            factor = AdjFactorEventHandlerHelper.get_factor_for_date(
                adj_factor_df, event_date_ymd, first_factor
            )
            
            # 获取该事件日的原始收盘价
            raw_close = raw_price_map.get(event_date_ymd)
            if raw_close is None or raw_close == 0:
                logger.debug(f"{stock_id} {event_date_ymd}: 无原始收盘价数据，跳过")
                continue
            
            # 获取该事件日的 EastMoney QFQ 价格
            eastmoney_qfq = eastmoney_qfq_map.get(event_date_ymd)
            
            # 计算 qfq_diff = raw_price - EastMoney_QFQ
            qfq_diff = AdjFactorEventHandlerHelper.calculate_qfq_diff(raw_close, eastmoney_qfq)
            
            if eastmoney_qfq is None:
                logger.debug(f"{stock_id} {event_date_ymd}: 无法获取东方财富前复权价格，qfq_diff 设为 0.0")
            
            events.append({
                'id': stock_id,
                'event_date': event_date_ymd,
                'factor': factor,
                'qfq_diff': qfq_diff
            })
        
        return events
