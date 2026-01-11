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

from .. import BaseDataService


class KlineService(BaseDataService):
    """K线数据服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化K线数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model - 私有属性，不对外暴露
        self._stock_kline = data_manager.get_model('stock_kline')
        self._adj_factor_event = data_manager.get_model('adj_factor_event')
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from app.core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default()
    
    # ==================== K线基础方法 ====================
    
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
            return self._stock_kline.load_by_date_range(stock_id, start_date, end_date)
        elif start_date:
            return self._stock_kline.load(
                "id = %s AND date >= %s",
                (stock_id, start_date),
                order_by="date ASC"
            )
        elif end_date:
            return self._stock_kline.load(
                "id = %s AND date <= %s",
                (stock_id, end_date),
                order_by="date ASC"
            )
        else:
            return self._stock_kline.load_by_stock(stock_id)
    
    def load_latest_kline(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载最新K线
        
        Args:
            stock_id: 股票代码
            
        Returns:
            最新K线数据，如果不存在返回 None
        """
        return self._stock_kline.load_latest(stock_id)
    
    def load_kline_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        加载指定日期的所有股票K线
        
        Args:
            date: 日期（格式：YYYYMMDD）
            
        Returns:
            K线数据列表
        """
        return self._stock_kline.load_by_date(date)
    
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
        qfq_price = raw_price - qfq_diff
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly，默认 daily）
            start_date: 开始日期（YYYYMMDD 或 YYYY-MM-DD，可选）
            end_date: 结束日期（YYYYMMDD 或 YYYY-MM-DD，可选）
        
        Returns:
            List[Dict]: 前复权K线数据列表，每条记录包含原始字段 + qfq_* 字段
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
    
    def load_multiple_terms(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict]]:
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
    
    def save_klines(self, klines: List[Dict[str, Any]]) -> int:
        """
        批量保存K线数据（自动去重）
        
        Args:
            klines: K线数据列表
            
        Returns:
            影响的行数
        """
        return self._stock_kline.save_klines(klines)
    
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
    
    # ==================== 私有方法（复权计算）====================
    
    def _load_raw_klines(
        self,
        stock_id: str,
        term: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """第一步：获取日期范围内的raw data"""
        if start_date and end_date:
            return self._stock_kline.load(
                "id = %s AND date >= %s AND date <= %s AND term = %s",
                (stock_id, start_date, end_date, term),
                order_by="date ASC"
            )
        elif start_date:
            return self._stock_kline.load(
                "id = %s AND date >= %s AND term = %s",
                (stock_id, start_date, term),
                order_by="date ASC"
            )
        elif end_date:
            return self._stock_kline.load(
                "id = %s AND date <= %s AND term = %s",
                (stock_id, end_date, term),
                order_by="date ASC"
            )
        else:
            return self._stock_kline.load(
                "id = %s AND term = %s",
                (stock_id, term),
                order_by="date ASC"
            )
    
    def _load_factor_events(
        self,
        stock_id: str,
        raw_klines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """第二步：获取日期范围内的复权因子事件"""
        from app.core.utils.date.date_utils import DateUtils
        
        # 确定日期范围
        kline_dates = [k.get('date') for k in raw_klines if k.get('date')]
        if not kline_dates:
            return []
        
        max_date = max(kline_dates)
        # 转换为 YYYYMMDD 格式（event_date 字段使用此格式）
        max_date_ymd = max_date.replace('-', '') if '-' in max_date else max_date
        
        # 加载所有 event_date <= max_date 的复权因子事件
        return self._adj_factor_event.load(
            "id = %s AND event_date <= %s",
            (stock_id, max_date_ymd),
            order_by="event_date ASC"
        )
    
    def _get_latest_factor(self, stock_id: str) -> Optional[float]:
        """第三步：获取最新复权因子 F(T)"""
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
        F_T: float
    ) -> List[Dict[str, Any]]:
        """
        第四步：遍历K线，让每个K线找到小于或等于当前时间最近的一个复权因子，并且加上diff变成复权后价格
        """
        from app.core.utils.date.date_utils import DateUtils
        
        qfq_klines = []
        event_idx = 0
        current_factor = 1.0
        current_qfq_diff = 0.0
        
        # 价格字段映射
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
            
            # 更新当前适用的因子
            while event_idx < len(factor_events):
                event = factor_events[event_idx]
                event_date = event.get('event_date')
                event_date_ymd = event_date.replace('-', '') if '-' in str(event_date) else str(event_date)
                
                if event_date_ymd <= kline_date_ymd:
                    factor_val = event.get('factor', 1.0)
                    qfq_diff_val = event.get('qfq_diff', 0.0)
                    current_factor = float(factor_val)
                    current_qfq_diff = float(qfq_diff_val)
                    event_idx += 1
                else:
                    break
            
            # 计算前复权价格：qfq_price = raw_price - qfq_diff
            applicable_qfq_diff = current_qfq_diff
            qfq_kline = kline.copy()
            
            # 计算前复权价格字段
            for field in price_fields:
                raw_value = kline.get(field)
                if raw_value is not None:
                    try:
                        raw_price = float(raw_value)
                        qfq_price = raw_price - applicable_qfq_diff
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
