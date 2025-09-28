#!/usr/bin/env python3
"""
数据加载器组件 - 根据策略设置加载和准备数据
"""
from typing import Dict, List, Any, Optional
import copy
from loguru import logger
from utils.db.db_manager import DatabaseManager
from app.analyzer.components.indicators import Indicators


class DataLoader:
    # 进程内只读缓存（非个股数据）
    _shared_cache: Dict[str, Any] = {}

    @staticmethod
    def _make_cache_key(dataset: str, start: Optional[str], end: Optional[str], categories: Optional[List[str]] = None) -> str:
        cats = tuple(sorted(categories)) if isinstance(categories, list) else None
        return f"{dataset}|{start or ''}|{end or ''}|{cats}"
    """数据加载器 - 根据策略设置加载和准备数据"""
    
    def __init__(self, db: DatabaseManager = None):
        """
        初始化数据加载器
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db

    @staticmethod
    def get_db() -> DatabaseManager:
        """
        获取数据库
        """
        try:
            from utils.db.db_manager import DatabaseManager
            db = DatabaseManager()
            db.initialize()
            return db
        except Exception as e:
            raise Exception(f"❌ 获取数据库失败: {e}")

    @staticmethod
    def load_stock_klines_data(stock_id: str, settings: Dict[str, Any], db: DatabaseManager = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载股票K线数据
        """
        min_required_base_records = settings.get('min_required_base_records', 0)
        min_required_kline_term = settings.get('base_term') 
        adjust = settings.get('adjust', 'qfq')
        allow_negative_records = settings.get('allow_negative_records', False)

        if db is None:
            db = DataLoader.get_db()

        from app.data_source.data_source_service import DataSourceService
        kline_data: Dict[str, List[Dict[str, Any]]] = {}

        kline_table = db.get_table_instance('stock_kline')
        adj_factor_table = db.get_table_instance('adj_factor')

        for term in settings.get('terms', []):
            records = kline_table.get_all_k_lines_by_term(stock_id, term)
            
            if adjust == 'qfq':
                qfq_factors = adj_factor_table.get_stock_factors(stock_id)
                DataSourceService.to_qfq(records, qfq_factors)
            elif adjust == 'hfq':
                hfq_factors = adj_factor_table.get_stock_factors(stock_id)
                DataSourceService.to_hfq(records, hfq_factors)

            if not allow_negative_records:
                records = DataSourceService.filter_out_negative_records(records)
            kline_data[term] = records

        if min_required_base_records > 0 and len(kline_data[min_required_kline_term]) < min_required_base_records:
            return None

        return kline_data

    @staticmethod
    def load_macro_data(settings: Dict[str, Any], db: DatabaseManager = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载宏观数据
        """
        macro_data = {}

        if db is None:
            db = DataLoader.get_db()

        start_date = settings.get('start_date')
        end_date = settings.get('end_date')

        if settings.get('GDP'):
            gdp_table = db.get_table_instance('gdp')
            macro_data['GDP'] = gdp_table.load_GDP(start_date, end_date)
        if settings.get('LPR'):
            lpr_table = db.get_table_instance('lpr')
            macro_data['LPR'] = lpr_table.load_LPR(start_date, end_date)
        if settings.get('Shibor'):
            shibor_table = db.get_table_instance('shibor')
            macro_data['Shibor'] = shibor_table.load_Shibor(start_date, end_date)
        if settings.get('price_indexes'):
            price_indexes_table = db.get_table_instance('price_indexes')

            requested = settings.get('price_indexes') or []
            if len(requested) == 0:
                requested = ['CPI', 'PPI', 'PMI', 'MoneySupply']

            # 统一一次性拉取，再按字段筛选，确保键值一致且只返回请求的键
            all_pi_rows = price_indexes_table.load_price_indexes(start_date, end_date) or []

            field_groups = {
                'CPI': ['CPI', 'CPI_yoy', 'CPI_mom'],
                'PPI': ['PPI', 'PPI_yoy', 'PPI_mom'],
                'PMI': ['PMI', 'PMI_l_scale', 'PMI_m_scale', 'PMI_s_scale'],
                'MoneySupply': ['M0', 'M0_yoy', 'M0_mom', 'M1', 'M1_yoy', 'M1_mom', 'M2', 'M2_yoy', 'M2_mom']
            }

            for key in requested:
                fields = field_groups.get(key)
                if not fields:
                    continue
                # 仅挑选 date + 请求的相关字段
                macro_data[key] = [
                    {k: row.get(k) for k in (['date'] + fields) if k in row}
                    for row in all_pi_rows
                ]

        return macro_data

    @staticmethod
    def load_corporate_finance_data(stock_id: str, settings: Dict[str, Any], db: DatabaseManager = None) -> Dict[str, List[Dict[str, Any]]]:

        if db is None:
            db = DataLoader.get_db()

        corporate_finance_data = {}

        start_date = settings.get('start_date')
        end_date = settings.get('end_date')
        categories = settings.get('categories') or []

        # 允许 categories 为空数组表示“全部”
        all_categories = [
            'growth', 'profit', 'cashflow', 'solvency', 'operation', 'asset'
        ]
        if isinstance(categories, list) and len(categories) == 0:
            categories = all_categories

        # 仅在有请求类别时读取
        if not categories:
            return corporate_finance_data

        table = db.get_table_instance('corporate_finance')

        # 映射类别到具体加载函数
        category_loader_map = {
            'growth': table.load_growth_indicators,
            'profit': table.load_profit_indicators,
            'cashflow': table.load_cashflow_indicators,
            'solvency': table.load_solvency_indicators,
            'operation': table.load_operation_indicators,
            'asset': table.load_asset_indicators,
        }

        for cat in categories:
            loader = category_loader_map.get(cat)
            if not loader:
                continue
            try:
                corporate_finance_data[cat] = loader(stock_id, start_date, end_date) or []
            except Exception:
                corporate_finance_data[cat] = []

        return corporate_finance_data

    @staticmethod
    def load_index_indicators_data(settings: Dict[str, Any], db: DatabaseManager = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载指数指标数据
        """
        if db is None:
            db = DataLoader.get_db()

        data: Dict[str, List[Dict[str, Any]]] = {}

        start_date = settings.get('start_date')
        end_date = settings.get('end_date')
        categories = settings.get('categories') or []

        # 空数组表示全部
        all_map = {
            'sh_index': '000001.SH',
            'sz_index': '399001.SZ',
            'hs_300': '000300.SH',
            'cyb_index': '399006.SZ',
            'kc_50': '000688.SH',
        }
        if isinstance(categories, list) and len(categories) == 0:
            categories = list(all_map.keys())

        # 缓存命中
        cache_key = DataLoader._make_cache_key('index_indicators', start_date, end_date, categories)
        cached = DataLoader._shared_cache.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)

        table = db.get_table_instance('stock_index_indicator')

        for cat in categories:
            if cat in all_map:
                idx = all_map[cat]
                data[cat] = table.load_index(idx, start_date, end_date) or []
            else:
                # 允许直接传入具体指数代码
                data[cat] = table.load_index(cat, start_date, end_date) or []

        # 写入缓存（深拷贝，确保只读语义）
        DataLoader._shared_cache[cache_key] = copy.deepcopy(data)
        return copy.deepcopy(data)
    
    @staticmethod
    def load_industry_capital_flow_data(settings: Dict[str, Any], db: DatabaseManager = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载行业资本流动数据
        """
        if db is None:
            db = DataLoader.get_db()

        start_date = settings.get('start_date')
        end_date = settings.get('end_date')

        # 缓存命中
        cache_key = DataLoader._make_cache_key('industry_capital_flow', start_date, end_date)
        cached = DataLoader._shared_cache.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)

        table = db.get_table_instance('industry_capital_flow')
        # 简单按日期范围拉取全部行业记录
        condition_parts = []
        params: List[str] = []
        if start_date:
            condition_parts.append("date >= %s")
            params.append(start_date)
        if end_date:
            condition_parts.append("date <= %s")
            params.append(end_date)
        condition = " AND ".join(condition_parts) if condition_parts else "1=1"

        records = table.load(condition=condition, params=tuple(params), order_by="date ASC") or []
        result = { 'all': records }
        # 写入缓存（深拷贝）
        DataLoader._shared_cache[cache_key] = copy.deepcopy(result)
        return copy.deepcopy(result)

    @staticmethod
    def prepare_data(stock: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        准备数据：在子进程内创建独立 DatabaseManager(use_connection_pool=False)，
        通过表 model API 加载所需周期数据，返回 { term: List[Dict] }。
        """

        data = {}

        stock_id = stock.get('id')
        db = DataLoader.get_db()

        # load klines data
        klines_settings = settings.get('klines')
        if not klines_settings:
            raise ValueError("klines settings is required")

        # load klines data
        data['klines'] = DataLoader.load_stock_klines_data(stock_id, klines_settings, db)

        if settings.get('klines', {}).get('indicators'):
            from app.analyzer.components.indicators import Indicators
            data['klines'] = Indicators.add_indicators(data['klines'], klines_settings['indicators'])

        # load macro data
        macro_settings = settings.get('macro')
        if macro_settings:
            data['macro'] = DataLoader.load_macro_data(macro_settings, db)

        # load corporate finance data
        corporate_finance_settings = settings.get('corporate_finance')
        if corporate_finance_settings:
            data['corporate_finance'] = DataLoader.load_corporate_finance_data(stock_id, corporate_finance_settings)

        # load index indicators data
        index_indicators_settings = settings.get('index_indicators')
        if index_indicators_settings:
            data['index_indicators'] = DataLoader.load_index_indicators_data(index_indicators_settings)

        # load industry capital flow data
        industry_capital_flow_settings = settings.get('industry_capital_flow')
        if industry_capital_flow_settings:
            data['industry_capital_flow'] = DataLoader.load_industry_capital_flow_data(industry_capital_flow_settings)

        return data



