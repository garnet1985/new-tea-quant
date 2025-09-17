#!/usr/bin/env python3
"""
DataLoader - 基于策略 settings 的统一数据加载器

用途：
- 根据 settings.klines 和 settings.simulation 加载各周期 K 线
- 提供按基础周期（base_term）的时间序列、批量迭代等便捷 API

注意：
- 建议传入经 PreprocessService.validate_settings 验证后的 settings；
  也支持传入原始 settings，本类会尽量提取需要的字段。
"""
from typing import Dict, Any, List, Iterable, Optional, Tuple
from loguru import logger

from app.conf.conf import data_default_start_date
from app.data_source.data_source_service import DataSourceService
from app.analyzer.libs.data_processor.indicators import Indicators



class DataLoader:
    def __init__(self):
        from utils.db.db_manager import DatabaseManager

        self.db = DatabaseManager(False)
        self.db.initialize()

        # 基础表实例
        self.kline_table = self.db.get_table_instance('stock_kline')
        self.index_table = self.db.get_table_instance('stock_index')
        self.adj_table = self.db.get_table_instance('adj_factor')

    # -----------------------------
    # Public APIs
    # -----------------------------
    def load_stock_klines_by_setting(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        上层（业务感知）API：
        - 根据 settings 解析 terms / 日期范围 / 复权方式
        - 调用底层数据获取函数拿到原始数据
        - 在此层做业务处理（如 QFQ 复权）

        Returns: { term: [records...] }
        """
        start_date, end_date, terms, adjust_factor = self._parse_kline_setting(settings)

        data = {}
        for term in terms:
            data[term] = self.load_stock_klines(stock_id, term, start_date, end_date, adjust_factor)

        # 应用技术指标（如有配置）
        indicators_conf = (settings.get('klines') or {}).get('indicators')
        if isinstance(indicators_conf, dict) and data:
            data = self._apply_indicators_to_terms(data, indicators_conf)

        return data

    def load_corporate_finance_by_setting(self, stock_id: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        # TODO: to be implemented later
        pass

    







    # -----------------------------
    # Low-level data access (no business)
    # -----------------------------
    def load_stock_klines(self, stock_id: str, term: str, start_date: str, end_date: Optional[str], adjust_factor: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        底层API：按显式参数返回某一周期在日期范围内的K线数据。
        若提供 adjust_factor='qfq'，对该 term 做前复权转换（仅限本term）。
        """
        where, params = self._build_kline_where_condition_by_date_range(stock_id, term, start_date, end_date)
        raw = self.kline_table.load(condition=where, params=params, order_by='date ASC')
        if adjust_factor == 'qfq':
            factors = self.fetch_adjust_factors(stock_id)
            adjusted_list = DataSourceService.to_qfq(raw, factors)
            return adjusted_list
        return raw

    def fetch_multi_kline_ranges(self, stock_id: str, terms: List[str], start_date: str, end_date: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        底层API：批量获取多周期的K线数据。无业务处理。
        """
        data: Dict[str, List[Dict[str, Any]]] = {}
        for term in terms or []:
            data[term] = self.load_stock_klines(stock_id, term, start_date, end_date)
        return data

    def fetch_adjust_factors(self, stock_id: str) -> List[Dict[str, Any]]:
        """
        底层API：获取原始复权因子序列。无任何业务逻辑。
        """
        return self.adj_table.load(condition="id = %s", params=(stock_id,), order_by="date ASC")





    







    # -----------------------------
    # Helpers
    # -----------------------------
    def _apply_indicators_to_terms(self, term_to_k: Dict[str, List[Dict[str, Any]]], indicators_conf: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        将指标配置应用到每个 term 的K线数据上。
        当前仅实现：moving_average
        """
        result: Dict[str, List[Dict[str, Any]]] = {}
        for term, k_lines in (term_to_k or {}).items():
            enriched = k_lines

            # 移动平均
            ma_conf = indicators_conf.get('moving_average') if isinstance(indicators_conf, dict) else None
            if isinstance(ma_conf, dict):
                periods = ma_conf.get('periods', []) or []
                price_field = ma_conf.get('price_field', 'close')
                for p in periods:
                    try:
                        enriched = Indicators.moving_average(enriched, int(p), price_field=price_field)
                    except Exception:
                        pass

            result[term] = enriched

        return result


    def _parse_kline_setting(self, settings: Dict[str, Any]) -> Tuple[str, Optional[str], List[str], str]:
        """
        解析 settings.kline 相关配置，返回 (start_date, end_date, terms, adjust_factor)
        """
        simulation = (settings.get('simulation') or {})
        start_date = simulation.get('start_date') or data_default_start_date
        end_date = simulation.get('end_date') or None

        klines = (settings.get('klines') or {})
        terms = klines.get('terms') or ['daily']
        adjust_factor = klines.get('adjust', 'qfq')
        return start_date, end_date, terms, adjust_factor


    def _build_kline_where_condition_by_date_range(self, stock_id: str, term: str, start_date: str, end_date: Optional[str]) -> Tuple[str, Tuple[Any, ...]]:
        if end_date:
            return (
                "id = %s AND term = %s AND date >= %s AND date <= %s",
                (stock_id, term, start_date, end_date),
            )
        return (
            "id = %s AND term = %s AND date >= %s",
            (stock_id, term, start_date),
        )
