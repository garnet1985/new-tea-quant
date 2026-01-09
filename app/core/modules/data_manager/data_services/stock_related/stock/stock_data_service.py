"""
股票数据服务（StockDataService）

职责：
- 封装股票相关的跨表查询和数据组装
- 提供领域级的业务方法

涉及的表：
- stock_list: 股票列表
- stock_kline: K线数据
- stock_labels: 股票标签
- adj_factor_event: 复权因子事件（adj_factor 已废弃）
"""
from typing import List, Dict, Any, Optional, Union
from loguru import logger

from .. import BaseDataService


class StockDataService(BaseDataService):
    """股票数据服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化股票数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # TODO: 这里应该是自动发现
        # 获取相关 Model（通过 DataManager，自动绑定默认 db）
        self.stock_list = data_manager.get_model('stock_list')
        self.stock_kline = data_manager.get_model('stock_kline')
        self.stock_labels = data_manager.get_model('stock_labels')
        # adj_factor 已废弃，使用 adj_factor_event 替代
        # self.adj_factor = data_manager.get_model('adj_factor')
        self.adj_factor_event = data_manager.get_model('adj_factor_event')
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from app.core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default()
    
    # ==================== 股票基础信息 ====================
    
    def load_stock_info(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载股票基本信息
        
        Args:
            stock_id: 股票代码
            
        Returns:
            股票信息字典，如果不存在返回 None
        """
        return self.stock_list.load_one("id = %s", (stock_id,))
    
    def load_all_stocks(self) -> List[Dict[str, Any]]:
        """
        加载所有股票列表
        
        Returns:
            股票列表
        """
        return self.stock_list.load_active_stocks()
    
    def load_filtered_stock_list(
        self, 
        exclude_patterns: Optional[Dict[str, List[str]]] = None,
        order_by: str = 'id'
    ) -> List[Dict[str, Any]]:
        """
        加载过滤后的股票列表（排除ST、科创板等）
        
        默认过滤规则（参考 analyzer_settings.py）：
        - 排除 id 以 "688" 开头的（科创板）
        - 排除 name 以 "*ST"、"ST"、"退" 开头的（ST股票和退市股票）
        - 注意：北交所（BJ）不排除（根据用户要求）
        
        Args:
            exclude_patterns: 自定义排除规则（可选）
                {
                    "start_with": {
                        "id": ["688"],
                        "name": ["*ST", "ST", "退"]
                    },
                    "contains": {
                        "id": ["BJ"]  # 如果需要排除北交所，可以传入
                    }
                }
            order_by: 排序字段（默认 'id'）
            
        Returns:
            List[Dict]: 过滤后的股票列表
        """
        # 默认过滤规则
        default_exclude = {
            "start_with": {
                "id": ["688"],  # 科创板
                "name": ["*ST", "ST", "退"]  # ST股票和退市股票
            },
            "contains": {
                # 注意：北交所（BJ）不排除（根据用户要求）
            }
        }
        
        # 合并用户自定义规则
        if exclude_patterns:
            exclude = exclude_patterns.copy()
            # 合并 start_with
            if "start_with" in exclude_patterns:
                exclude["start_with"] = {
                    **default_exclude["start_with"],
                    **exclude_patterns["start_with"]
                }
            else:
                exclude["start_with"] = default_exclude["start_with"]
            # 合并 contains
            if "contains" in exclude_patterns:
                exclude["contains"] = {
                    **default_exclude["contains"],
                    **exclude_patterns["contains"]
                }
            else:
                exclude["contains"] = default_exclude["contains"]
        else:
            exclude = default_exclude
        
        # 加载所有活跃股票
        all_stocks = self.stock_list.load_active_stocks()
        
        # 应用过滤规则
        filtered_stocks = []
        for stock in all_stocks:
            stock_id = str(stock.get('id', ''))
            stock_name = str(stock.get('name', ''))
            
            # 检查是否应该排除
            should_exclude = False
            
            # 检查 start_with 规则
            for field, patterns in exclude.get("start_with", {}).items():
                value = stock_id if field == "id" else stock_name
                for pattern in patterns:
                    if value.startswith(pattern):
                        should_exclude = True
                        break
                if should_exclude:
                    break
            
            # 检查 contains 规则
            if not should_exclude:
                for field, patterns in exclude.get("contains", {}).items():
                    value = stock_id if field == "id" else stock_name
                    for pattern in patterns:
                        if pattern in value:
                            should_exclude = True
                            break
                    if should_exclude:
                        break
            
            if not should_exclude:
                filtered_stocks.append(stock)
        
        # 排序
        if order_by:
            try:
                filtered_stocks.sort(key=lambda x: x.get(order_by, ''))
            except Exception as e:
                logger.warning(f"排序失败，使用默认排序: {e}")
                filtered_stocks.sort(key=lambda x: x.get('id', ''))
        
        return filtered_stocks
    
    # ==================== K线数据 ====================
    
    def load_kline_series(
        self, 
        stock_id: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载K线序列
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            K线数据列表
        """
        if start_date and end_date:
            return self.stock_kline.load_by_date_range(stock_id, start_date, end_date)
        elif start_date:
            return self.stock_kline.load(
                "id = %s AND date >= %s",
                (stock_id, start_date),
                order_by="date ASC"
            )
        elif end_date:
            return self.stock_kline.load(
                "id = %s AND date <= %s",
                (stock_id, end_date),
                order_by="date ASC"
            )
        else:
            return self.stock_kline.load_by_stock(stock_id)
    
    def load_latest_kline(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载最新K线
        
        Args:
            stock_id: 股票代码
            
        Returns:
            最新K线数据，如果不存在返回 None
        """
        return self.stock_kline.load_latest(stock_id)
    
    def load_kline_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        加载指定日期的所有股票K线
        
        Args:
            date: 日期（格式：YYYYMMDD）
            
        Returns:
            K线数据列表
        """
        return self.stock_kline.load_by_date(date)
    
    def load_qfq_klines(
        self,
        stock_id: str,
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载前复权（QFQ）K线数据
        
        使用新的 adj_factor_event 表计算前复权价格：
        qfq_price = raw_price × F(t) / F(T) + constantDiff
        
        其中：
        - F(t): 交易日期的复权因子（从 adj_factor_event 查询）
        - F(T): 最新复权因子
        - constantDiff: 与东方财富前复权价格的固定差异
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly，默认 daily）
            start_date: 开始日期（YYYYMMDD 或 YYYY-MM-DD，可选）
            end_date: 结束日期（YYYYMMDD 或 YYYY-MM-DD，可选）
        
        Returns:
            List[Dict]: 前复权K线数据列表，每条记录包含原始字段 + qfq_* 字段：
                - 原始字段：id, term, date, open, close, highest, lowest, pre_close, ...
                - 前复权字段：qfq_open, qfq_close, qfq_high, qfq_low, qfq_pre_close
        """
        # 第一步：获取日期范围内的raw data
        raw_klines = self._load_raw_klines(stock_id, term, start_date, end_date)
        if not raw_klines:
            return []
        
        # 第二步：获取日期范围内的复权因子事件
        factor_events = self._load_factor_events(stock_id, raw_klines)
        if not factor_events:
            logger.warning(f"{stock_id} 没有复权因子事件，返回原始K线数据")
            return raw_klines
        
        # 第三步：计算日期范围内的复权因子F(t) / F(T)（获取F(T)）
        F_T = self._get_latest_factor(stock_id)
        if F_T is None:
            logger.warning(f"{stock_id} 没有最新复权因子，返回原始K线数据")
            return raw_klines
        
        # 第四步：遍历K线，让每个K线找到小于或等于当前时间最近的一个复权因子，并且加上diff变成复权后价格
        qfq_klines = self._apply_qfq_adjustment(raw_klines, factor_events, F_T)
        
        return qfq_klines
    
    def _load_raw_klines(
        self,
        stock_id: str,
        term: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        第一步：获取日期范围内的raw data
        
        Args:
            stock_id: 股票代码
            term: 周期
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            原始K线数据列表
        """
        if start_date and end_date:
            # ⚠️ 修复：load_by_date_range 没有过滤 term，需要显式添加 term 过滤
            return self.stock_kline.load(
                "id = %s AND date >= %s AND date <= %s AND term = %s",
                (stock_id, start_date, end_date, term),
                order_by="date ASC"
            )
        elif start_date:
            return self.stock_kline.load(
                "id = %s AND date >= %s AND term = %s",
                (stock_id, start_date, term),
                order_by="date ASC"
            )
        elif end_date:
            return self.stock_kline.load(
                "id = %s AND date <= %s AND term = %s",
                (stock_id, end_date, term),
                order_by="date ASC"
            )
        else:
            return self.stock_kline.load(
                "id = %s AND term = %s",
                (stock_id, term),
                order_by="date ASC"
            )
    
    def _load_factor_events(
        self,
        stock_id: str,
        raw_klines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        第二步：获取日期范围内的复权因子事件
        
        Args:
            stock_id: 股票代码
            raw_klines: 原始K线数据列表
        
        Returns:
            复权因子事件列表，按日期升序排列
        """
        from app.core.utils.date.date_utils import DateUtils
        
        # 确定日期范围
        kline_dates = [k.get('date') for k in raw_klines if k.get('date')]
        if not kline_dates:
            return []
        
        max_date = max(kline_dates)
        # 转换为 YYYYMMDD 格式（event_date 字段使用此格式）
        max_date_ymd = max_date.replace('-', '') if '-' in max_date else max_date
        
        # 加载所有 event_date <= max_date 的复权因子事件
        # 注意：我们需要该日期之前的所有因子事件，而不仅仅是该日期范围内的事件
        return self.adj_factor_event.load(
            "id = %s AND event_date <= %s",
            (stock_id, max_date_ymd),
            order_by="event_date ASC"
        )
    
    def _get_latest_factor(self, stock_id: str) -> Optional[float]:
        """
        第三步：获取最新复权因子 F(T)
        
        Args:
            stock_id: 股票代码
        
        Returns:
            最新复权因子 F(T)，如果不存在返回 None
        """
        latest_event = self.adj_factor_event.load_latest_factor(stock_id)
        if not latest_event:
            return None
        
        factor = latest_event.get('factor')
        if factor is None:
            return None
        
        # 确保返回 float 类型
        return float(factor)
    
    def _apply_qfq_adjustment(
        self,
        raw_klines: List[Dict[str, Any]],
        factor_events: List[Dict[str, Any]],
        F_T: float
    ) -> List[Dict[str, Any]]:
        """
        第四步：遍历K线，让每个K线找到小于或等于当前时间最近的一个复权因子，并且加上diff变成复权后价格
        
        Args:
            raw_klines: 原始K线数据列表
            factor_events: 复权因子事件列表（已按日期升序排列）
            F_T: 最新复权因子 F(T)
        
        Returns:
            前复权K线数据列表
        """
        from app.core.utils.date.date_utils import DateUtils
        
        qfq_klines = []
        event_idx = 0  # 当前复权事件索引
        current_factor = 1.0  # 当前适用的复权因子（默认1.0）
        current_qfq_diff = 0.0  # 当前适用的前复权价格差异（默认0.0）
        
        # 价格字段映射：K线数据中使用 highest/lowest，计算后使用 qfq_high/qfq_low
        price_fields = ['open', 'close', 'highest', 'lowest', 'pre_close']
        field_mapping = {
            'highest': 'high',
            'lowest': 'low'
        }
        
        for kline in raw_klines:
            kline_date = kline.get('date')
            if not kline_date:
                continue
            
            # K线日期统一为 YYYYMMDD 格式
            kline_date_ymd = kline_date.replace('-', '') if '-' in kline_date else kline_date
            
            # 更新当前适用的因子：找到所有 event_date <= kline_date 的事件，使用最新的
            while event_idx < len(factor_events):
                event = factor_events[event_idx]
                event_date = event.get('event_date')
                
                # event_date 已经是 YYYYMMDD 格式的字符串
                event_date_ymd = event_date.replace('-', '') if '-' in str(event_date) else str(event_date)
                
                if event_date_ymd <= kline_date_ymd:
                    # 这个事件适用于当前K线日期，更新当前因子
                    factor_val = event.get('factor', 1.0)
                    qfq_diff_val = event.get('qfq_diff', 0.0)
                    current_factor = float(factor_val)
                    current_qfq_diff = float(qfq_diff_val)
                    event_idx += 1
                else:
                    # 后续事件日期都大于当前K线日期，停止更新
                    break
            
            # 计算前复权价格
            # 根据最新结论：在除权日之间的区间内，Tushare 裸价 与 EastMoney 前复权价 的差值为常量 qfq_diff
            # 因此这里直接使用 qfq_price = raw_price - qfq_diff
            F_t = current_factor  # 预留字段，当前算法不再使用 F_t / F_T
            applicable_qfq_diff = current_qfq_diff
            
            # 复制原始K线数据
            qfq_kline = kline.copy()
            
            # 计算前复权价格字段
            for field in price_fields:
                raw_value = kline.get(field)
                if raw_value is not None:
                    try:
                        raw_price = float(raw_value)
                        # EastMoney 风格前复权：qfq_price = raw_price - qfq_diff
                        qfq_price = raw_price - applicable_qfq_diff
                        # 使用映射后的字段名（highest -> high, lowest -> low）
                        output_field = field_mapping.get(field, field)
                        qfq_kline[f'qfq_{output_field}'] = qfq_price
                    except (ValueError, TypeError):
                        output_field = field_mapping.get(field, field)
                        qfq_kline[f'qfq_{output_field}'] = None
                else:
                    output_field = field_mapping.get(field, field)
                    qfq_kline[f'qfq_{output_field}'] = None
            
            qfq_klines.append(qfq_kline)
        
        return qfq_klines
    
    # ==================== 跨表查询（SQL JOIN）====================
    
    def load_stock_with_latest_kline(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载股票信息 + 最新K线（SQL JOIN）
        
        Args:
            stock_id: 股票代码
            
        Returns:
            包含股票信息和最新K线的字典，如果不存在返回 None
        """
        sql = """
        SELECT 
            s.*,
            k.date as kline_date,
            k.open, k.high, k.low, k.close, k.volume, k.amount
        FROM stock_list s
        LEFT JOIN stock_kline k ON s.id = k.id
        WHERE s.id = %s
        ORDER BY k.date DESC
        LIMIT 1
        """
        results = self.db.execute_sync_query(sql, (stock_id,))
        return results[0] if results else None
    
    def load_stocks_with_kline_by_date(self, date: str) -> List[Dict[str, Any]]:
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
    
    def load_stock_with_labels(
        self, 
        stock_id: str, 
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        加载股票信息 + 标签（SQL JOIN）
        
        Args:
            stock_id: 股票代码
            date: 日期（可选，如果提供则只查询该日期的标签）
            
        Returns:
            包含股票信息和标签列表的字典
        """
        # 先获取股票信息
        stock_info = self.load_stock_info(stock_id)
        if not stock_info:
            return {}
        
        # 查询标签
        if date:
            labels = self.stock_labels.load(
                "id = %s AND date = %s",
                (stock_id, date)
            )
        else:
            labels = self.stock_labels.load("id = %s", (stock_id,))
        
        stock_info['labels'] = labels
        return stock_info
    
    # ==================== 批量操作 ====================
    
    def save_stocks(self, stocks: List[Dict[str, Any]]) -> int:
        """
        批量保存股票列表（自动去重）
        
        Args:
            stocks: 股票数据列表
            
        Returns:
            影响的行数
        """
        return self.stock_list.save_stocks(stocks)
    
    def save_klines(self, klines: List[Dict[str, Any]]) -> int:
        """
        批量保存K线数据（自动去重）
        
        Args:
            klines: K线数据列表
            
        Returns:
            影响的行数
        """
        return self.stock_kline.save_klines(klines)
    
    def load_multiple_terms(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """
        加载多个周期的K线数据（兼容 KlineLoader 接口）
        
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
            # 使用 load_qfq_klines 方法（如果 adjust='qfq'）
            if adjust == 'qfq':
                records = self.load_qfq_klines(stock_id, term, start_date, end_date)
            else:
                # 对于其他复权方式，使用原始数据加载
                records = self.load_kline_series(stock_id, start_date, end_date)
                # 过滤 term
                records = [r for r in records if r.get('term') == term]
            
            kline_data[term] = records
        
        # 检查最小记录数要求
        if min_required_base_records > 0:
            base_records = kline_data.get(min_required_kline_term, [])
            if len(base_records) < min_required_base_records:
                # 返回包含所有请求term的空列表
                return {term: [] for term in settings.get('terms', [])}
        
        return kline_data
    
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
        加载K线数据（兼容 KlineLoader 接口）
        
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
            result = self.load_qfq_klines(stock_id, term, start_date, end_date)
        else:
            # 对于其他复权方式，返回原始数据
            result = self.load_kline_series(stock_id, start_date, end_date)
            # 过滤 term
            result = [r for r in result if r.get('term') == term]
        
        if as_dataframe:
            import pandas as pd
            return pd.DataFrame(result) if result else pd.DataFrame()
        
        return result

