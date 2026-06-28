"""
K线数据服务（KlineService）

职责：
- 封装K线相关的查询和数据操作
- 提供前复权计算功能（方案 B：raw×F/F(最新)+C，见 adj_factor_event README）
- 处理多周期K线加载

涉及的表：
- stock_kline: K线数据
- adj_factor_event: 复权因子事件
"""
from typing import List, Dict, Any, Optional, Sequence, Union
import logging

from ... import BaseDataService
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)

# 价格字段配置（用于复权计算）
_PRICE_FIELDS = ['open', 'close', 'high', 'low', 'pre_close']


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
        self._stock_kline = data_manager.get_table("sys_stock_klines")
        self._adj_factor_event = data_manager.get_table("sys_adj_factor_events")
        
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

    def load_latest_date(self, term: str = "daily") -> str:
        """
        加载 **全市场** 指定周期最新 K 线日期（YYYYMMDD）。

        与 ``load_latest(stock_id)`` 的区别：不依赖单只股票。
        行情入库进度；优先用 ``calendar.get_db_latest_completed_trading_date()``。
        """
        if not self._stock_kline:
            return ""
        return str(self._stock_kline.load_latest_date(term)).strip()

    def load_earliest_date(
        self,
        term: str = "daily",
        stock_ids: Optional[Sequence[str]] = None,
    ) -> str:
        """
        加载指定周期最早 K 线日期（YYYYMMDD）。

        ``stock_ids`` 未传或为空：全市场该周期最早日期。
        传入本次回测样本股票 id 列表：仅在该样本内取最早日期。
        """
        if not self._stock_kline:
            return ""
        return str(self._stock_kline.load_earliest_date(term, stock_ids=stock_ids)).strip()

    def load_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        加载指定日期的所有股票K线
        
        Args:
            date: 日期（格式：YYYYMMDD）
            
        Returns:
            K线数据列表
        """
        return self._stock_kline.load_by_date(date)
    
    def _query_qfq_join_rows(
        self,
        stock_id: str,
        term: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        JOIN 查询：K 线 + (event_date <= k.date) 最近复权事件。
        返回原始查询结果（含 adj_event_date/adj_factor/adj_qfq_diff）。
        """
        sql = """
        SELECT 
            k.*,
            e.event_date as adj_event_date,
            e.factor as adj_factor,
            e.qfq_anchor as adj_qfq_anchor,
            e.raw_anchor as adj_raw_anchor,
            e.qfq_diff as adj_qfq_diff
        FROM sys_stock_klines k
        LEFT JOIN sys_adj_factor_events e ON (
            e.id = k.id 
            AND e.event_date = (
                SELECT MAX(e2.event_date)
                FROM sys_adj_factor_events e2
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
        return self.db.execute_sync_query(sql, params) or []

    def _resolve_effective_event_map(
        self,
        *,
        stock_id: str,
        results: List[Dict[str, Any]],
        is_strict: bool,
    ) -> Dict[str, Dict[str, Any]]:
        if not self._adj_factor_event:
            return {}
        # 优先复用 JOIN 结果中已带出的 adj_* 列，减少额外 IO。
        return self._adj_factor_event.load_effective_events_from_join_rows(
            stock_id=stock_id,
            rows=results,
            is_strict=is_strict,
        )

    def _build_qfq_rows_strict(
        self,
        *,
        stock_id: str,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        严格输出：仅使用命中的历史事件；未命中时按原价（不复权）。
        """
        return self._build_qfq_rows_from_join_results(
            stock_id=stock_id,
            results=results,
            is_strict=True,
        )

    def _build_qfq_rows_default(
        self,
        *,
        stock_id: str,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        默认连续输出：无历史事件时沿用最早可用事件的起始补偿。
        """
        return self._build_qfq_rows_from_join_results(
            stock_id=stock_id,
            results=results,
            is_strict=False,
        )

    def _build_qfq_rows_from_join_results(
        self,
        *,
        stock_id: str,
        results: List[Dict[str, Any]],
        is_strict: bool,
    ) -> List[Dict[str, Any]]:
        event_map = self._resolve_effective_event_map(
            stock_id=stock_id,
            results=results,
            is_strict=is_strict,
        )
        events = self._load_stock_adj_factor_events(stock_id)
        factor_latest = self._latest_factor_from_events(events)
        global_qfq_context = self._resolve_global_qfq_context(
            events,
            factor_latest=factor_latest,
        )
        qfq_klines: List[Dict[str, Any]] = []
        for row in results:
            qfq_kline = dict(row)
            date_key = self._normalize_date(qfq_kline.get("date"))
            default_info = (
                {"qfq_diff": 0.0, "is_adjusted": False, "is_inferred": False}
                if not is_strict
                else {"qfq_diff": 0.0, "is_adjusted": False}
            )
            info = event_map.get(date_key, default_info)

            qfq_kline.pop("adj_event_date", None)
            qfq_kline.pop("adj_factor", None)
            qfq_kline.pop("adj_qfq_diff", None)

            self._apply_qfq_from_event_info(
                qfq_kline,
                info,
                factor_latest=factor_latest,
                global_qfq_context=global_qfq_context,
            )
            qfq_klines.append(qfq_kline)
        return qfq_klines

    def load_qfq_split(
        self,
        stock_id: str,
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        *,
        is_strict: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        前复权：K 线与复权事件分两次简单查询，在内存合并（无大 JOIN）。

        返回行的 ``open/close/high/low`` 即为前复权价（非 ``qfq_*`` 宽列）。
        与 ``load_qfq(..., use_join=False)`` 等价，单独暴露便于批量路径复用。
        """
        start_date = self._normalize_date(start_date)
        end_date = self._normalize_date(end_date)

        raw_klines = self.load_raw(stock_id, term, start_date, end_date)
        if not raw_klines:
            return []

        events = self._load_stock_adj_factor_events(stock_id)

        return self._merge_qfq_from_raw_and_events(
            stock_id=stock_id,
            term=term,
            raw_rows=raw_klines,
            events=events,
            is_strict=is_strict,
        )

    def load_qfq_strict(
        self,
        stock_id: str,
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        *,
        use_join: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        严格模式前复权：
        - 仅使用 event_date <= k.date 的最近复权事件；
        - 若找不到事件，不推断，保持未复权原价。

        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly，默认 daily）
            start_date: 开始日期（YYYYMMDD 或 YYYY-MM-DD，可选）
            end_date: 结束日期（YYYYMMDD 或 YYYY-MM-DD，可选）
        
        Returns:
            List[Dict]: 严格前复权K线数据列表
        """
        return self.load_qfq(
            stock_id,
            term,
            start_date,
            end_date,
            is_strict=True,
            use_join=use_join,
        )

    def load_qfq(
        self,
        stock_id: str,
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_strict: bool = False,
        *,
        use_join: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        前复权加载统一入口：
        - use_join=False（默认）：``load_qfq_split``，K 线 + 复权事件分查后在内存合并
        - use_join=True：单条 SQL 大 JOIN
        - is_strict=False（默认连续）：查询起点前无事件时，用该股最早事件的 anchor 向前补偿
        - is_strict=True（严格）：缺历史事件不推断，保持未复权原价
        - 复权计算：``raw×F(段)/F(最新) + C``，``C`` 由**最新事件** anchor 折算；``qfq_diff`` 仅 anchor 缺失时应急

        返回 ``open/close/high/low`` 为前复权价（与 ``load_raw`` 列名一致，语义由本方法决定）。
        """
        if not use_join:
            return self.load_qfq_split(
                stock_id,
                term,
                start_date,
                end_date,
                is_strict=is_strict,
            )

        start_date = self._normalize_date(start_date)
        end_date = self._normalize_date(end_date)

        try:
            results = self._query_qfq_join_rows(stock_id, term, start_date, end_date)
            if not results:
                return []
            if is_strict:
                return self._build_qfq_rows_strict(stock_id=stock_id, results=results)
            return self._build_qfq_rows_default(stock_id=stock_id, results=results)
        except Exception as e:
            logger.error(f"查询 QFQ K 线数据失败: {e}")
            logger.warning("回退到拆分查询 + 内存合并")
            return self.load_qfq_split(
                stock_id,
                term,
                start_date,
                end_date,
                is_strict=is_strict,
            )
    
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
        
        # 前复权：batch raw + 全量 adj 事件 + 内存 merge（F(最新) 取该股最新除权）
        if adjust == 'qfq':
            adj_by_stock = self._load_adj_events_for_qfq_batch(stock_ids)
            for stock_id in stock_ids:
                klines = result.get(stock_id) or []
                if not klines:
                    continue
                result[stock_id] = self._merge_qfq_from_raw_and_events(
                    stock_id=stock_id,
                    term=term,
                    raw_rows=klines,
                    events=adj_by_stock.get(stock_id) or [],
                )

        return result

    def _load_adj_events_for_qfq_batch(
        self,
        stock_ids: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """QFQ 批量路径：``id IN (...)`` 加载每只股票全部复权事件。"""
        if not stock_ids or not self._adj_factor_event:
            return {sid: [] for sid in stock_ids}

        placeholders = ','.join(['%s'] * len(stock_ids))
        where_clause = f"id IN ({placeholders})"
        params: tuple = tuple(stock_ids)

        all_events = (
            self._adj_factor_event.load(
                where_clause,
                params,
                order_by="id ASC, event_date ASC",
            )
            or []
        )

        result: Dict[str, List[Dict[str, Any]]] = {stock_id: [] for stock_id in stock_ids}
        for event in all_events:
            stock_id = event.get('id')
            if stock_id in result:
                result[stock_id].append(event)

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
        
        if not self._adj_factor_event:
            return klines
        eff_map = self._adj_factor_event.load_effective_events_for_dates(
            stock_id=stock_id,
            dates=[self._normalize_date(k.get("date")) for k in klines if k.get("date")],
            is_strict=False,
        )
        events = self._load_stock_adj_factor_events(stock_id)
        factor_latest = self._latest_factor_from_events(events)
        global_qfq_context = self._resolve_global_qfq_context(
            events,
            factor_latest=factor_latest,
        )
        result = []
        for kline in klines:
            kline_date = kline.get('date')
            if not kline_date:
                result.append(kline)
                continue
            
            qfq_kline = kline.copy()
            info = eff_map.get(self._normalize_date(kline_date), {})
            self._apply_qfq_from_event_info(
                qfq_kline,
                info,
                factor_latest=factor_latest,
                global_qfq_context=global_qfq_context,
            )
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
            # 已经是 DataFrame：直接返回；否则从记录列表构建 DataFrame
            if isinstance(result, pd.DataFrame):
                return result
            return pd.DataFrame(result or [])
        
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
                - qfq_anchor / raw_anchor: 事件日快照（主路径）
                - qfq_diff: 可选应急缓存，仅消费端 anchor 缺失时回退
            
        Returns:
            影响的行数
        """
        return self._adj_factor_event.save_events(events)

    def load_adj_factor_events(
        self,
        stock_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        加载指定股票的复权因子事件序列。
        """
        if not self._adj_factor_event:
            return []

        conditions = ["id = %s"]
        params: List[Any] = [stock_id]
        if start_date:
            conditions.append("event_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("event_date <= %s")
            params.append(end_date)
        where_clause = " AND ".join(conditions)
        return self._adj_factor_event.load(where_clause, tuple(params), order_by="event_date ASC")

    def load_adj_factor_events_batch(
        self,
        stock_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量加载多个股票的复权因子事件序列（优化：一次查询所有股票）。

        Args:
            stock_ids: 股票代码列表
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            Dict[stock_id, List[Dict]]: 每只股票的复权因子事件字典
        """
        if not self._adj_factor_event or not stock_ids:
            return {}

        # 使用 IN 子句批量查询
        placeholders = ','.join(['%s'] * len(stock_ids))
        conditions = [f"id IN ({placeholders})"]
        params: List[Any] = list(stock_ids)

        if start_date:
            conditions.append("event_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("event_date <= %s")
            params.append(end_date)

        where_clause = " AND ".join(conditions)
        all_rows = self._adj_factor_event.load(where_clause, tuple(params), order_by="id ASC, event_date ASC")

        # 按 stock_id 分组
        result: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in stock_ids}
        for row in all_rows:
            sid = row.get("id", "")
            if sid in result:
                result[sid].append(row)

        return result
    
    def delete_adj_factor_events(self, stock_id: str) -> int:
        """
        删除指定股票的所有复权因子事件
        
        Args:
            stock_id: 股票代码
            
        Returns:
            影响的行数
        """
        return self._adj_factor_event.delete("id = %s", (stock_id,))

    def update_adj_factor_last_update(self, stock_id: str) -> int:
        """
        仅更新指定股票的 last_update 时间戳（无复权变化时调用）。
        
        Returns:
            影响的行数
        """
        return self._adj_factor_event.update_last_update_for_stock(stock_id)
    
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
        FROM sys_stock_list s
        LEFT JOIN sys_stock_klines k ON s.id = k.id AND k.term = %s
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
        FROM sys_stock_list s
        INNER JOIN sys_stock_klines k ON s.id = k.id
        WHERE k.date = %s
        ORDER BY s.id ASC
        """
        return self.db.execute_sync_query(sql, (date,))
    
    # ==================== 私有方法（复权计算）====================

    def _effective_event_map_in_memory(
        self,
        *,
        raw_rows: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        is_strict: bool,
    ) -> Dict[str, Dict[str, Any]]:
        """
        基于已加载的复权事件行，在内存构造 date -> 生效事件信息（不再查库）。
        规则对齐 ``AdjFactorEventModel.load_effective_events_for_dates``。
        """
        normalized_dates = sorted(
            {
                d
                for d in (self._normalize_date(r.get("date")) for r in raw_rows)
                if d is not None
            }
        )
        if not normalized_dates:
            return {}

        max_date = normalized_dates[-1]
        filtered = [
            e
            for e in events
            if self._normalize_date(e.get("event_date")) is not None
            and self._normalize_date(e.get("event_date")) <= max_date
        ]
        earliest_event = None if is_strict else (events[0] if events else None)

        out: Dict[str, Dict[str, Any]] = {}
        event_idx = 0
        latest_event = None
        n = len(filtered)
        for d in normalized_dates:
            while event_idx < n:
                ed = self._normalize_date(filtered[event_idx].get("event_date"))
                if ed is not None and ed <= d:
                    latest_event = filtered[event_idx]
                    event_idx += 1
                else:
                    break

            selected = latest_event
            inferred = False
            if selected is None and (not is_strict) and earliest_event is not None:
                selected = earliest_event
                inferred = True

            if selected is None:
                out[d] = {
                    "event": None,
                    "qfq_diff": 0.0,
                    "is_adjusted": False,
                    "is_inferred": False,
                }
            else:
                qfq_diff = selected.get("qfq_diff") or 0.0
                out[d] = {
                    "event": selected,
                    "qfq_diff": qfq_diff,
                    "is_adjusted": True,
                    "is_inferred": inferred,
                }
        return out

    def _merge_qfq_from_raw_and_events(
        self,
        *,
        stock_id: str,
        term: str = "daily",
        raw_rows: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        is_strict: bool = False,
    ) -> List[Dict[str, Any]]:
        """将原始 K 线与已加载的复权事件在内存合并为前复权 K 线。"""
        if not raw_rows:
            return []

        event_map = self._effective_event_map_in_memory(
            raw_rows=raw_rows,
            events=events,
            is_strict=is_strict,
        )
        factor_latest = self._latest_factor_from_events(events)
        global_qfq_context = self._resolve_global_qfq_context(
            events,
            factor_latest=factor_latest,
        )
        qfq_klines: List[Dict[str, Any]] = []
        for row in raw_rows:
            qfq_kline = dict(row)
            date_key = self._normalize_date(qfq_kline.get("date"))
            info = event_map.get(
                date_key,
                {"event": None, "qfq_diff": 0.0, "is_adjusted": False, "is_inferred": False},
            )

            self._apply_qfq_from_event_info(
                qfq_kline,
                info,
                factor_latest=factor_latest,
                global_qfq_context=global_qfq_context,
            )
            qfq_klines.append(qfq_kline)
        return qfq_klines

    def _load_qfq_fallback(
        self,
        stock_id: str,
        term: str,
        start_date: Optional[str],
        end_date: Optional[str],
        *,
        is_strict: bool = False,
    ) -> List[Dict[str, Any]]:
        """JOIN 失败时的回退：拆分查询 + 内存合并。"""
        return self.load_qfq_split(
            stock_id,
            term,
            start_date,
            end_date,
            is_strict=is_strict,
        )
     
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
        return DateUtils.normalize_str(date_str)
    
    def _load_stock_adj_factor_events(self, stock_id: str) -> List[Dict[str, Any]]:
        """加载单只股票全部复权事件（F(最新) 与 anchor 均依赖完整序列）。"""
        if not self._adj_factor_event:
            return []
        return (
            self._adj_factor_event.load(
                "id = %s",
                (stock_id,),
                order_by="event_date ASC",
            )
            or []
        )

    @staticmethod
    def _latest_factor_from_events(events: List[Dict[str, Any]]) -> float:
        if not events:
            return 1.0
        return events[-1].get("factor") or 1.0

    @staticmethod
    def _resolve_global_qfq_context(
        events: List[Dict[str, Any]],
        *,
        factor_latest: float,
    ) -> Dict[str, Any]:
        """
        方案 B：全局 offset 由最新事件 anchor 折算::

            C = qfq_anchor_最新 - raw_anchor_最新 × F_最新 / F(最新)
            qfq(t) = raw(t) × F(段) / F(最新) + C
        """
        if not events or factor_latest <= 0:
            return {"use_global_offset": False, "global_offset": 0.0}

        latest = events[-1]
        qfq_anchor = latest.get("qfq_anchor")
        raw_anchor = latest.get("raw_anchor")
        if qfq_anchor is not None and raw_anchor is not None:
            factor_n = latest.get("factor") or 1.0
            if factor_n <= 0:
                factor_n = 1.0
            return {
                "use_global_offset": True,
                "global_offset": (
                    float(qfq_anchor)
                    - float(raw_anchor) * float(factor_n) / factor_latest
                ),
            }

        logger.warning(
            "最新复权事件缺少 anchor，无法折算全局 offset: stock=%s event_date=%s",
            latest.get("id"),
            latest.get("event_date"),
        )
        return {"use_global_offset": False, "global_offset": 0.0}

    @staticmethod
    def _qfq_price_global_offset(
        raw_price: float,
        *,
        factor_eff: float,
        factor_latest: float,
        global_offset: float,
    ) -> float:
        """``raw × F(段)/F(最新) + C``（C 由最新 anchor 折算）。"""
        if factor_latest <= 0:
            return raw_price
        return raw_price * factor_eff / factor_latest + global_offset

    @staticmethod
    def _qfq_price_from_anchor(
        raw_price: float,
        *,
        qfq_anchor: float,
        raw_anchor: float,
        factor_eff: float,
        factor_latest: float,
    ) -> float:
        """
        前复权主路径（anchor）::

            qfq(t) = qfq_anchor + (raw(t) - raw_anchor) × F(段) / F(最新)
        """
        if factor_latest <= 0:
            return raw_price
        scale = factor_eff / factor_latest
        return qfq_anchor + (raw_price - raw_anchor) * scale

    @staticmethod
    def _qfq_price_from_diff_fallback(
        raw_price: float,
        *,
        factor_eff: float,
        factor_latest: float,
        qfq_diff: float,
    ) -> float:
        """
        应急回退（非主路径）::

            qfq(t) = raw(t) × F(段) / F(最新) + qfq_diff

        仅当事件行缺少 ``qfq_anchor`` 或 ``raw_anchor`` 时使用。
        """
        if factor_latest <= 0:
            return raw_price
        return raw_price * factor_eff / factor_latest + qfq_diff

    def _apply_qfq_from_event_info(
        self,
        kline: Dict[str, Any],
        info: Dict[str, Any],
        *,
        factor_latest: float,
        global_qfq_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        按生效事件对 OHLC 应用前复权，结果写回 ``open/close/high/low/pre_close``。

        主路径：``raw×F(段)/F(最新) + C``（C 由最新事件 anchor 折算，段内 ``F(段)`` 仍按当日生效事件）。
        最新事件缺 anchor 时，回退段内 ``qfq_diff`` 应急。
        """
        event = info.get("event")
        if not event:
            return

        factor_eff = event.get("factor") or 1.0
        if factor_eff <= 0:
            factor_eff = 1.0

        ctx = global_qfq_context or {"use_global_offset": False, "global_offset": 0.0}
        if ctx.get("use_global_offset"):
            global_offset = float(ctx.get("global_offset") or 0.0)
            for field in _PRICE_FIELDS:
                raw_value = kline.get(field)
                if raw_value is None:
                    kline[field] = None
                    continue
                kline[field] = self._qfq_price_global_offset(
                    float(raw_value),
                    factor_eff=factor_eff,
                    factor_latest=factor_latest,
                    global_offset=global_offset,
                )
            return

        qfq_anchor = event.get("qfq_anchor")
        raw_anchor = event.get("raw_anchor")
        has_anchor = qfq_anchor is not None and raw_anchor is not None

        if not has_anchor:
            stock_id = event.get("id") or kline.get("id")
            event_date = event.get("event_date")
            logger.warning(
                "复权事件缺少 anchor，应急回退 qfq_diff: stock=%s event_date=%s",
                stock_id,
                event_date,
            )
            qfq_diff = info.get("qfq_diff")
            if qfq_diff is None:
                qfq_diff = event.get("qfq_diff")
            if qfq_diff is None:
                qfq_diff = 0.0

            for field in _PRICE_FIELDS:
                raw_value = kline.get(field)
                if raw_value is None:
                    kline[field] = None
                    continue
                kline[field] = self._qfq_price_from_diff_fallback(
                    float(raw_value),
                    factor_eff=factor_eff,
                    factor_latest=factor_latest,
                    qfq_diff=float(qfq_diff),
                )
            return

        for field in _PRICE_FIELDS:
            raw_value = kline.get(field)
            if raw_value is None:
                kline[field] = None
                continue
            kline[field] = self._qfq_price_global_offset(
                float(raw_value),
                factor_eff=factor_eff,
                factor_latest=factor_latest,
                global_offset=0.0,
            )
