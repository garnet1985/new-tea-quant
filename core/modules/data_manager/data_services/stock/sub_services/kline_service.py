"""
K线数据服务（KlineService）

职责：
- 封装K线相关的查询和数据操作
- 提供前复权计算功能
- 处理多周期K线加载

涉及的表：
- stock_kline: K线数据
- adj_factor_event: 复权因子事件
"""
from typing import List, Dict, Any, Optional, Union
from loguru import logger

from ... import BaseDataService
from core.utils import DateUtils

# 价格字段配置（用于复权计算）
_PRICE_FIELDS = ['open', 'close', 'highest', 'lowest', 'pre_close']


class KlineService(BaseDataService):
    """K线数据服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化K线数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model（表名由 DataManager 发现并注册）
        self._stock_kline = data_manager.get_table("sys_stock_kline_daily")
        self._adj_factor_event = data_manager.get_table("sys_adj_factor_event")
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default(auto_init=True)
    
    # ==================== K线基础方法 ====================

    def load_raw(
        self,
        stock_id: str,
        term: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """加载原始K线数据（内部方法）"""
        # 构建查询条件
        conditions = ["id = %s"]
        params = [stock_id]
        
        if term:
            conditions.append("term = %s")
            params.append(term)
        
        if start_date:
            conditions.append("date >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("date <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        return self._stock_kline.load(where_clause, tuple(params), order_by="date ASC")
   
    
    def load_latest(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载最新K线
        
        Args:
            stock_id: 股票代码
            
        Returns:
            最新K线数据，如果不存在返回 None
        """
        return self._stock_kline.load_latest(stock_id)
    
    def load_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        加载指定日期的所有股票K线
        
        Args:
            date: 日期（格式：YYYYMMDD）
            
        Returns:
            K线数据列表
        """
        return self._stock_kline.load_by_date(date)
    
    def load_qfq(
        self,
        stock_id: str,
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载前复权（QFQ）K线数据
        
        使用新的 adj_factor_event 表计算前复权价格：
        qfq_price = raw_price - qfq_diff
        
        优化：使用 JOIN 一次查询出所有需要的数据，减少数据库查询次数
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly，默认 daily）
            start_date: 开始日期（YYYYMMDD 或 YYYY-MM-DD，可选）
            end_date: 结束日期（YYYYMMDD 或 YYYY-MM-DD，可选）
        
        Returns:
            List[Dict]: 前复权K线数据列表，每条记录包含原始字段 + qfq_* 字段
        """
        # 统一日期格式为 YYYYMMDD
        start_date = self._normalize_date(start_date)
        end_date = self._normalize_date(end_date)
        
        # 使用 JOIN 一次查询出 K 线数据和对应的复权因子事件
        # 优化方案：使用窗口函数（ROW_NUMBER）替代相关子查询，性能更好
        # 对于每个 K 线日期，找到小于等于该日期的最近一个复权因子事件
        # ⚠️  性能问题：相关子查询在 JOIN 中对每条 K 线执行一次
        # - 平均每只股票: ~3190 条 K 线
        # - 相关子查询执行次数: ~3190 次/股票
        # - 虽然只有 1 条 SQL 语句，但内部执行了大量子查询
        # - 导致单次查询时间从 38.73ms 增加到 171.61ms（4.4倍）
        #
        # 💡 优化方向（待实施）：
        # 1. 使用派生表预计算每个日期对应的最新因子（减少子查询执行次数）
        # 2. 使用窗口函数（如果 MySQL 版本支持，MySQL 8.0+）
        # 3. 或者回退到多次查询方式（3 次简单查询可能比 1 次复杂查询快）
        #
        # 当前实现：使用相关子查询（兼容性好，但性能较差）
        sql = """
        SELECT 
            k.*,
            e.event_date as adj_event_date,
            e.factor as adj_factor,
            e.qfq_diff as adj_qfq_diff
        FROM stock_kline k
        LEFT JOIN adj_factor_event e ON (
            e.id = k.id 
            AND e.event_date = (
                SELECT MAX(e2.event_date)
                FROM adj_factor_event e2
                WHERE e2.id = k.id 
                AND e2.event_date <= k.date
            )
        )
        WHERE k.id = %s AND k.term = %s
            AND (k.date >= %s OR %s IS NULL)
            AND (k.date <= %s OR %s IS NULL)
        ORDER BY k.date ASC
        """
        
        params = (stock_id, term, start_date, start_date, end_date, end_date)
        
        try:
            results = self.db.execute_sync_query(sql, params)
            if not results:
                return []
            
            # 转换结果并计算 QFQ 价格
            qfq_klines = []
            for row in results:
                qfq_kline = dict(row)
                
                # 获取复权因子信息
                qfq_diff = qfq_kline.get('adj_qfq_diff')
                if qfq_diff is None:
                    # 如果没有复权因子事件，使用默认值 0.0
                    qfq_diff = 0.0
                else:
                    qfq_diff = float(qfq_diff)
                
                # 移除临时字段
                qfq_kline.pop('adj_event_date', None)
                qfq_kline.pop('adj_factor', None)
                qfq_kline.pop('adj_qfq_diff', None)
                
                # 计算前复权价格字段
                self._apply_qfq_prices(qfq_kline, qfq_diff)
                
                qfq_klines.append(qfq_kline)
            
            return qfq_klines
            
        except Exception as e:
            logger.error(f"查询 QFQ K 线数据失败: {e}")
            # 如果 JOIN 查询失败，回退到原来的多次查询方式
            logger.warning(f"回退到多次查询方式")
            return self._load_qfq_fallback(stock_id, term, start_date, end_date)
    
    def load_multiple(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """
        加载多个周期的K线数据
        
        Args:
            stock_id: 股票代码
            settings: 配置字典，包含terms、adjust、allow_negative_records等
            
        Returns:
            Dict[term, List[Dict]]: 各周期的K线数据
        """
        min_required_base_records = settings.get('min_required_base_records', 0)
        min_required_kline_term = settings.get('signal_base_term', 'daily')
        adjust = settings.get('adjust', 'qfq')
        allow_negative_records = settings.get('allow_negative_records', False)
        
        # 从 settings 中提取 start_date 和 end_date（如果存在）
        start_date = settings.get('start_date')
        end_date = settings.get('end_date')
        
        kline_data = {}
        
        for term in settings.get('terms', []):
            # 使用 load_qfq 方法（如果 adjust='qfq'）
            if adjust == 'qfq':
                records = self.load_qfq(stock_id, term, start_date, end_date)
            else:
                # 对于其他复权方式，使用原始数据加载
                records = self.load_raw(stock_id, term, start_date, end_date)
            
            kline_data[term] = records
        
        # 检查最小记录数要求
        if min_required_base_records > 0:
            base_records = kline_data.get(min_required_kline_term, [])
            if len(base_records) < min_required_base_records:
                # 返回包含所有请求term的空列表
                return {term: [] for term in settings.get('terms', [])}
        
        return kline_data
    
    def load_batch(
        self,
        stock_ids: List[str],
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'qfq',
        filter_negative: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量加载多个股票的K线数据（优化：一次查询所有股票）
        
        Args:
            stock_ids: 股票代码列表
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust: 复权方式（qfq前复权/hfq后复权/none不复权）
            filter_negative: 是否过滤负值（默认True）
            
        Returns:
            Dict[stock_id, List[Dict]]: 每只股票的K线数据字典
        """
        if not stock_ids:
            return {}
        
        # 统一日期格式
        start_date = self._normalize_date(start_date)
        end_date = self._normalize_date(end_date)
        
        # 批量查询原始K线数据（使用 IN 子句）
        placeholders = ','.join(['%s'] * len(stock_ids))
        conditions = [f"id IN ({placeholders})"]
        params = list(stock_ids)
        
        if term:
            conditions.append("term = %s")
            params.append(term)
        
        if start_date:
            conditions.append("date >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("date <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        all_klines = self._stock_kline.load(where_clause, tuple(params), order_by="id ASC, date ASC")
        
        # 按股票ID分组
        result: Dict[str, List[Dict[str, Any]]] = {stock_id: [] for stock_id in stock_ids}
        
        for kline in all_klines:
            stock_id = kline.get('id')
            if stock_id in result:
                result[stock_id].append(kline)
        
        # 如果需要前复权，批量查询所有股票的复权事件，然后对每只股票的数据进行复权计算
        if adjust == 'qfq':
            # 批量查询所有股票的复权事件（一次查询）
            batch_adj_events = self._load_batch_adj_events(stock_ids) if self._adj_factor_event else {}
            
            for stock_id in stock_ids:
                if result[stock_id]:
                    adj_events = batch_adj_events.get(stock_id, [])
                    result[stock_id] = self._apply_qfq_to_klines(result[stock_id], stock_id, adj_events)
        
        return result
    
    def _load_batch_adj_events(self, stock_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量加载多个股票的复权因子事件
        
        Args:
            stock_ids: 股票代码列表
            
        Returns:
            Dict[stock_id, List[Dict]]: 每只股票的复权事件列表
        """
        if not stock_ids or not self._adj_factor_event:
            return {}
        
        # 批量查询所有股票的复权事件（使用 IN 子句）
        placeholders = ','.join(['%s'] * len(stock_ids))
        where_clause = f"id IN ({placeholders})"
        all_events = self._adj_factor_event.load(where_clause, tuple(stock_ids), order_by="id ASC, event_date ASC")
        
        # 按股票ID分组
        result: Dict[str, List[Dict[str, Any]]] = {stock_id: [] for stock_id in stock_ids}
        for event in all_events:
            stock_id = event.get('id')
            if stock_id in result:
                result[stock_id].append(event)
        
        return result
    
    def _apply_qfq_to_klines(
        self, 
        klines: List[Dict[str, Any]], 
        stock_id: str,
        adj_events: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        对K线数据应用前复权计算（批量版本）
        
        Args:
            klines: 原始K线数据列表
            stock_id: 股票代码
            
        Returns:
            前复权后的K线数据列表
        """
        if not klines:
            return []
        
        # 如果没有提供复权事件，尝试加载（向后兼容）
        if adj_events is None:
            adj_events = self._adj_factor_event.load(
                "id = %s",
                (stock_id,),
                order_by="event_date ASC"
            ) if self._adj_factor_event else []
        
        # 如果没有复权事件，直接返回原始数据
        if not adj_events:
            return klines
        
        # 构建复权事件索引（按日期）
        event_map = {e['event_date']: e for e in adj_events}
        event_dates = sorted(event_map.keys())
        
        # 对每条K线应用复权
        result = []
        for kline in klines:
            kline_date = kline.get('date')
            if not kline_date:
                result.append(kline)
                continue
            
            # 找到小于等于该日期的最近一个复权事件
            latest_event = None
            for event_date in event_dates:
                if event_date <= kline_date:
                    latest_event = event_map[event_date]
                else:
                    break
            
            # 复制K线数据
            qfq_kline = kline.copy()
            
            # 如果有复权事件，应用复权
            if latest_event:
                qfq_diff = latest_event.get('qfq_diff', 0.0)
                # 应用前复权：价格 = 原始价格 - qfq_diff
                for price_field in ['open', 'close', 'highest', 'lowest', 'pre_close']:
                    if price_field in qfq_kline and qfq_kline[price_field] is not None:
                        qfq_kline[f'qfq_{price_field}'] = qfq_kline[price_field] - qfq_diff
                        # 同时保留原始字段
                qfq_kline['adj_event_date'] = latest_event.get('event_date')
                qfq_kline['adj_factor'] = latest_event.get('factor')
            else:
                # 没有复权事件，qfq价格等于原始价格
                for price_field in ['open', 'close', 'highest', 'lowest', 'pre_close']:
                    if price_field in qfq_kline:
                        qfq_kline[f'qfq_{price_field}'] = qfq_kline[price_field]
            
            result.append(qfq_kline)
        
        return result
    
    def load(
        self, 
        stock_id: str, 
        term: str = 'daily', 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        adjust: str = 'qfq', 
        filter_negative: bool = True,
        as_dataframe: bool = False
    ) -> Union[List[Dict], Any]:
        """
        加载K线数据（兼容接口）
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust: 复权方式（qfq前复权/hfq后复权/none不复权）
            filter_negative: 是否过滤负值（默认True，暂不支持）
            as_dataframe: 是否返回DataFrame（默认False返回List[Dict]）
            
        Returns:
            DataFrame or List[Dict]: K线数据
        """
        if adjust == 'qfq':
            result = self.load_qfq(stock_id, term, start_date, end_date)
        else:
            # 对于其他复权方式，返回原始数据
            result = self.load_raw(stock_id, term, start_date, end_date)
        
        if as_dataframe:
            import pandas as pd
            return pd.DataFrame(result) if result else pd.DataFrame()
        
        return result
    
    def save(self, klines: List[Dict[str, Any]]) -> int:
        """
        批量保存K线数据（自动去重）
        
        Args:
            klines: K线数据列表
            
        Returns:
            影响的行数
        """
        return self._stock_kline.save_klines(klines)
    
    def save_adj_factor_events(self, events: List[Dict[str, Any]]) -> int:
        """
        批量保存复权因子事件（自动去重）
        
        Args:
            events: 复权因子事件列表，每个事件必须包含：
                - id: 股票代码
                - event_date: 除权日期（YYYYMMDD）
                - factor: 复权因子
                - qfq_diff: 价格差异（可选，默认0.0）
            
        Returns:
            影响的行数
        """
        return self._adj_factor_event.save_events(events)
    
    def delete_adj_factor_events(self, stock_id: str) -> int:
        """
        删除指定股票的所有复权因子事件
        
        Args:
            stock_id: 股票代码
            
        Returns:
            影响的行数
        """
        return self._adj_factor_event.delete("id = %s", (stock_id,))
    
    def load_with_latest(self, stock_id: str, term: str = 'daily') -> Optional[Dict[str, Any]]:
        """
        加载股票信息 + 最新K线（SQL JOIN）
        
        Args:
            stock_id: 股票代码
            term: 周期（默认 'daily'）
            
        Returns:
            包含股票信息和最新K线的字典，如果不存在返回 None
        """
        sql = """
        SELECT 
            s.*,
            k.date as kline_date,
            k.open, k.high, k.low, k.close, k.volume, k.amount
        FROM stock_list s
        LEFT JOIN stock_kline k ON s.id = k.id AND k.term = %s
        WHERE s.id = %s
        ORDER BY k.date DESC
        LIMIT 1
        """
        results = self.db.execute_sync_query(sql, (term, stock_id))
        return results[0] if results else None
    
    def load_all_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        加载指定日期的所有股票信息 + K线（SQL JOIN）
        
        Args:
            date: 日期（格式：YYYYMMDD）
            
        Returns:
            股票信息 + K线数据列表
        """
        sql = """
        SELECT 
            s.*,
            k.open, k.high, k.low, k.close, k.volume, k.amount
        FROM stock_list s
        INNER JOIN stock_kline k ON s.id = k.id
        WHERE k.date = %s
        ORDER BY s.id ASC
        """
        return self.db.execute_sync_query(sql, (date,))
    
    # ==================== 私有方法（复权计算）====================
    
    def _load_qfq_fallback(
        self,
        stock_id: str,
        term: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        回退方法：使用多次查询的方式加载 QFQ K 线数据
        
        当 JOIN 查询失败时使用此方法
        """
        # 获取日期范围内的raw data
        raw_klines = self.load_raw(stock_id, term, start_date, end_date)
        if not raw_klines:
            return []
        
        # 获取日期范围内的复权因子事件
        factor_events = self._load_factor_events(stock_id, raw_klines)
        if not factor_events:
            logger.warning(f"{stock_id} 没有复权因子事件，返回原始K线数据")
            return raw_klines
        
        # 获取最新复权因子（保留以兼容接口）
        F_T = self._get_latest_factor(stock_id) or 1.0
        
        # 遍历K线，让每个K线找到小于或等于当前时间最近的一个复权因子，并且加上diff变成复权后价格
        return self._apply_qfq_adjustment(raw_klines, factor_events, F_T)
     
    def _load_factor_events(
        self,
        stock_id: str,
        raw_klines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """获取日期范围内的复权因子事件"""
        # 确定日期范围
        kline_dates = [k.get('date') for k in raw_klines if k.get('date')]
        if not kline_dates:
            return []
        
        max_date = max(kline_dates)
        # 转换为 YYYYMMDD 格式（event_date 字段使用此格式）
        max_date_ymd = self._normalize_date(max_date)
        
        # 加载所有 event_date <= max_date 的复权因子事件
        return self._adj_factor_event.load(
            "id = %s AND event_date <= %s",
            (stock_id, max_date_ymd),
            order_by="event_date ASC"
        )
    
    def _get_latest_factor(self, stock_id: str) -> Optional[float]:
        """获取最新复权因子 F(T)"""
        latest_event = self._adj_factor_event.load_latest_factor(stock_id)
        if not latest_event:
            return None
        
        factor = latest_event.get('factor')
        if factor is None:
            return None
        
        return float(factor)
    
    def _apply_qfq_adjustment(
        self,
        raw_klines: List[Dict[str, Any]],
        factor_events: List[Dict[str, Any]],
        F_T: float  # 保留参数以保持接口兼容性（虽然未使用）
    ) -> List[Dict[str, Any]]:
        """
        遍历K线，让每个K线找到小于或等于当前时间最近的一个复权因子，并且加上diff变成复权后价格
        
        Args:
            raw_klines: 原始K线数据列表
            factor_events: 复权因子事件列表
            F_T: 最新复权因子（保留以兼容接口，实际未使用）
        """
        qfq_klines = []
        event_idx = 0
        current_qfq_diff = 0.0
        
        for kline in raw_klines:
            kline_date = kline.get('date')
            if not kline_date:
                continue
            
            # K线日期统一为 YYYYMMDD 格式
            kline_date_ymd = self._normalize_date(kline_date)
            
            # 更新当前适用的因子（找到小于等于当前K线日期的最近事件）
            while event_idx < len(factor_events):
                event = factor_events[event_idx]
                event_date = event.get('event_date')
                event_date_ymd = self._normalize_date(str(event_date))
                
                if event_date_ymd <= kline_date_ymd:
                    current_qfq_diff = float(event.get('qfq_diff', 0.0))
                    event_idx += 1
                else:
                    break
            
            # 计算前复权价格：qfq_price = raw_price - qfq_diff
            qfq_kline = kline.copy()
            self._apply_qfq_prices(qfq_kline, current_qfq_diff)
            qfq_klines.append(qfq_kline)
        
        return qfq_klines
    
    # ==================== 辅助方法 ====================
    
    @staticmethod
    def _normalize_date(date_str: Optional[str]) -> Optional[str]:
        """
        统一日期格式为 YYYYMMDD
        
        Args:
            date_str: 日期字符串（YYYYMMDD 或 YYYY-MM-DD 格式，或 None）
            
        Returns:
            YYYYMMDD 格式的日期字符串，如果输入为 None 则返回 None
        """
        return DateUtils.normalize_date(date_str)
    
    @staticmethod
    def _apply_qfq_prices(kline: Dict[str, Any], qfq_diff: float) -> None:
        """
        对K线数据应用前复权价格计算
        
        Args:
            kline: K线数据字典（会被修改）
            qfq_diff: 前复权差异值
        """
        for field in _PRICE_FIELDS:
            raw_value = kline.get(field)
            
            if raw_value is not None:
                try:
                    raw_price = float(raw_value)
                    qfq_price = raw_price - qfq_diff
                    kline[f'qfq_{field}'] = qfq_price
                except (ValueError, TypeError):
                    kline[f'qfq_{field}'] = None
            else:
                kline[f'qfq_{field}'] = None
