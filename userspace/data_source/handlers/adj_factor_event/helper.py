"""
复权因子事件 Handler 的辅助函数集合

将复杂的业务逻辑拆分为语义化的静态方法，便于测试和维护。
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import pandas as pd
from datetime import date

from core.utils.date.date_utils import DateUtils


class AdjFactorEventHandlerHelper:
    """复权因子事件处理器的辅助函数集合"""
    
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
        elif market == 'BJ':
            return f"5.{code}"
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
                logger.debug("东方财富 API 返回的数据不是 dict 类型")
                return qfq_map
            
            # 检查 API 返回的错误码
            if eastmoney_result.get('rc') != 0:
                logger.warning(f"东方财富 API 返回错误码: {eastmoney_result.get('rc')}, 消息: {eastmoney_result.get('rt')}")
            
            data = eastmoney_result.get('data')
            if not data:
                logger.debug(f"东方财富 API 返回的 data 为空，完整响应: {eastmoney_result}")
                return qfq_map
            
            klines = data.get('klines', [])
            if not klines:
                logger.debug(f"东方财富 API 返回的 klines 为空，data: {data}")
                return qfq_map
            
            # klines 格式：["2024-12-15,11.46", "2024-12-14,11.45", ...]
            # 第一个字段是日期（YYYY-MM-DD），第二个字段是收盘价
            parsed_count = 0
            failed_count = 0
            sample_dates = []  # 记录前几个解析成功的日期，用于调试
            
            for kline_str in klines:
                if not isinstance(kline_str, str):
                    failed_count += 1
                    continue
                    
                parts = kline_str.split(',')
                if len(parts) >= 2:
                    date_str = parts[0].strip()  # YYYY-MM-DD，去除空格
                    try:
                        close_price = float(parts[1].strip())
                        # 转换为 YYYYMMDD 格式
                        date_ymd = date_str.replace('-', '')
                        
                        # 验证日期格式（应该是8位数字）
                        if len(date_ymd) == 8 and date_ymd.isdigit():
                            qfq_map[date_ymd] = close_price
                            parsed_count += 1
                            # 记录前3个日期用于调试
                            if len(sample_dates) < 3:
                                sample_dates.append(date_ymd)
                        else:
                            logger.debug(f"日期格式不正确: {date_str} -> {date_ymd}")
                            failed_count += 1
                    except (ValueError, IndexError) as e:
                        logger.debug(f"解析东方财富 kline 数据失败: {kline_str}, 错误: {e}")
                        failed_count += 1
                        continue
                else:
                    failed_count += 1
            
            # 记录解析统计信息
            # if parsed_count > 0:
                # earliest = min(qfq_map.keys()) if qfq_map else 'N/A'
                # latest = max(qfq_map.keys()) if qfq_map else 'N/A'
                # logger.debug(
                #     f"成功解析东方财富数据: {parsed_count} 条，失败: {failed_count} 条，"
                #     f"日期范围: {earliest} ~ {latest}, 样本日期: {sample_dates}"
                # )
            # else:
            #     logger.warning(
            #         f"东方财富数据解析失败: 总数据 {len(klines)} 条，全部解析失败。"
            #         f"前3条原始数据: {klines[:3] if len(klines) >= 3 else klines}"
            #     )
                
        except Exception as e:
            logger.warning(f"解析东方财富 API 数据失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return qfq_map
    
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
            default_factor: 默认因子（如果找不到数据，通常用于第一根K线早于所有复权因子数据的情况）
        
        Returns:
            float: 复权因子
        """
        if adj_factor_df is None or adj_factor_df.empty:
            return default_factor
        
        # 查找该事件日的复权因子
        event_row = adj_factor_df[adj_factor_df['trade_date'] == event_date_ymd]
        if not event_row.empty:
            return float(event_row.iloc[0]['adj_factor'])
        
        # 如果事件日不在复权因子数据中（如第一根日线早于所有复权因子数据），
        # 使用该日期之前最近的因子
        prev_rows = adj_factor_df[adj_factor_df['trade_date'] <= event_date_ymd]
        if not prev_rows.empty:
            return float(prev_rows.iloc[-1]['adj_factor'])
        
        # 如果该日期之前也没有数据（第一根K线早于所有复权因子数据），
        # 使用第一个可用的复权因子（而不是默认因子1.0）
        # 这样可以确保第一根K线使用正确的初始复权因子
        if not adj_factor_df.empty:
            first_row = adj_factor_df.iloc[0]
            return float(first_row.get('adj_factor', default_factor))
        
        # 如果完全没有数据，使用默认因子
        return default_factor
    
    @staticmethod
    def get_raw_price_for_date(raw_price_map: Dict[str, float], event_date_ymd: str) -> Optional[float]:
        """
        获取指定日期的原始收盘价
        
        如果事件日不是交易日（如周末、节假日），查找该日期之前最近的交易日收盘价
        
        Args:
            raw_price_map: 日期 -> 原始收盘价的映射（YYYYMMDD格式）
            event_date_ymd: 事件日期（YYYYMMDD格式）
        
        Returns:
            float: 原始收盘价，如果找不到返回 None
        """
        # 首先尝试直接获取事件日的收盘价
        raw_close = raw_price_map.get(event_date_ymd)
        if raw_close is not None and raw_close > 0:
            return raw_close
        
        # 如果事件日没有收盘价（可能不是交易日），查找该日期之前最近的交易日
        # 将日期字符串转换为整数进行比较
        event_date_int = int(event_date_ymd)
        
        # 找到所有早于或等于事件日的日期，按降序排序，取第一个
        available_dates = [
            (int(date_str), price) 
            for date_str, price in raw_price_map.items() 
            if price > 0 and int(date_str) <= event_date_int
        ]
        
        if available_dates:
            # 按日期降序排序，取最近的交易日
            available_dates.sort(reverse=True)
            return available_dates[0][1]
        
        # 如果找不到任何数据，返回 None
        return None
    
    @staticmethod
    def get_eastmoney_qfq_for_date(eastmoney_qfq_map: Dict[str, float], event_date_ymd: str, stock_id: str = None) -> Optional[float]:
        """
        获取指定日期的东方财富前复权价格
        
        如果事件日不是交易日（如周末、节假日），查找该日期之前最近的交易日价格
        
        Args:
            eastmoney_qfq_map: 日期 -> 东方财富前复权价格的映射（YYYYMMDD格式）
            event_date_ymd: 事件日期（YYYYMMDD格式）
            stock_id: 股票代码（可选，用于日志）
        
        Returns:
            float: 前复权价格，如果找不到返回 None
        """
        if not eastmoney_qfq_map:
            return None
        
        # 首先尝试直接获取事件日的价格
        qfq_price = eastmoney_qfq_map.get(event_date_ymd)
        if qfq_price is not None:
            # 检查价格类型，如果不是数字类型则尝试转换
            if not isinstance(qfq_price, (int, float)):
                try:
                    qfq_price = float(qfq_price)
                except (ValueError, TypeError):
                    logger.error(f"{stock_id or 'Unknown'} {event_date_ymd}: 无法将价格转换为 float: {qfq_price}")
                    return None
            return float(qfq_price)
        
        # 如果事件日没有价格（可能不是交易日），查找该日期之前最近的交易日
        # 将日期字符串转换为整数进行比较
        event_date_int = int(event_date_ymd)
        
        # 找到所有早于或等于事件日的日期，按降序排序，取第一个
        # 注意：即使价格为 0 或负数，也包含在内（可能是有效数据）
        available_dates = [
            (int(date_str), price) 
            for date_str, price in eastmoney_qfq_map.items() 
            if price is not None and int(date_str) <= event_date_int
        ]
        
        if available_dates:
            # 按日期降序排序，取最近的交易日
            available_dates.sort(reverse=True)
            return available_dates[0][1]
        
        # 如果找不到任何数据，返回 None
        return None
    
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
    
    # ========== 日期工具类 ==========
    
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
            return DateUtils.date_to_format(date_value)
        elif isinstance(date_value, str):
            # 使用 normalize_str 自动识别并转换格式
            normalized = DateUtils.normalize_str(date_value)
            if normalized:
                return normalized
            # 如果 normalize_str 失败，尝试手动处理
            if '-' in date_value:
                return date_value.replace('-', '')
            return date_value
        else:
            return str(date_value).replace('-', '')
    
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
        
        # 获取第一个复权因子（用于从未有复权事件的股票，或第一根K线早于所有复权因子数据的情况）
        first_factor = 1.0
        if not adj_factor_df.empty:
            first_row = adj_factor_df.iloc[0]
            first_factor = float(first_row.get('adj_factor', 1.0))
        
        # 计算所有复权事件日期（因子变化的日期）
        changing_dates = AdjFactorEventHandlerHelper.get_factor_changing_dates(adj_factor_df)
        
        # 确保第一根日线日期作为一个事件点（必须包含，即使早于所有复权因子数据）
        # 注意：first_kline_ymd 应该来自 EastMoney 的第一个K线日期（因为复权因子依赖 EastMoney 的前复权价格）
        # 这样可以确保第一根K线的复权因子与 EastMoney 的前复权价格保持一致
        if first_kline_ymd:
            if first_kline_ymd not in changing_dates:
                # 插入到开头，确保第一根K线日期是第一个事件
                changing_dates.insert(0, first_kline_ymd)
            else:
                # 如果已经在列表中，确保它在第一位
                changing_dates.remove(first_kline_ymd)
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
            # 如果事件日不是交易日（如周末、节假日），查找该日期之前最近的交易日收盘价
            raw_close = AdjFactorEventHandlerHelper.get_raw_price_for_date(
                raw_price_map, event_date_ymd
            )
            if raw_close is None or raw_close == 0:
                # 事件日没有原始收盘价属于正常情况，不再逐条打印 debug 日志
                continue
            
            # 获取该事件日的 EastMoney QFQ 价格
            # 如果事件日不是交易日，查找该日期之前最近的交易日价格
            eastmoney_qfq = AdjFactorEventHandlerHelper.get_eastmoney_qfq_for_date(
                eastmoney_qfq_map, event_date_ymd, stock_id
            )
            
            # 计算 qfq_diff = raw_price - EastMoney_QFQ
            qfq_diff = AdjFactorEventHandlerHelper.calculate_qfq_diff(raw_close, eastmoney_qfq)
            
            if eastmoney_qfq is None:
                logger.warning(f"{stock_id} {event_date_ymd}: 无法获取东方财富前复权价格")
            
            events.append({
                'id': stock_id,
                'event_date': event_date_ymd,
                'factor': factor,
                'qfq_diff': qfq_diff
            })
        
        return events
