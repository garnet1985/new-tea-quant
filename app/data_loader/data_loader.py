#!/usr/bin/env python3
"""
数据加载服务 - 全局数据服务工具类

位置：app/data_loader/（应用层，与analyzer、data_source并列）

职责：
- 提供各种业务需求的数据服务
- 处理跨表操作和数据聚合
- 封装数据处理逻辑（复权、过滤、指标计算等）

架构：
- DataLoader: 主入口，统一API
- KlineLoader: K线数据专用加载器
- MacroLoader: 宏观数据加载器（待实现）
- Helpers: 工具类（复权、过滤等）

设计原则：
- 按业务领域分层（stock/macro/finance）
- 提供便捷方法（80%场景零配置）
- 保留灵活方法（20%场景全配置）
- 支持多进程（静态工厂方法）
"""
from typing import Dict, List, Any, Optional, Union
import copy
import pandas as pd
from loguru import logger
from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_service import DataSourceService

from .loaders import KlineLoader
from .loaders import LabelLoader
from utils.db.tables.stock_labels.model import StockLabelModel


class DataLoader:
    """
    数据加载服务（统一工具类）
    
    职责：
    - 股票数据：K线、复权、股票信息
    - 宏观数据：GDP、LPR、SHIBOR、物价指数
    - 财务数据：企业财务指标
    - 市场数据：指数、资金流
    
    使用方式：
        from app.data_loader import DataLoader
        
        loader = DataLoader(db)
        df = loader.load_klines('000001.SZ', adjust='qfq')
    """
    
    # 进程内只读缓存（非个股数据）
    _shared_cache: Dict[str, Any] = {}
    
    def __init__(self, db: DatabaseManager = None):
        """
        初始化数据加载器
        
        Args:
            db: 数据库管理器实例（可选，不传会自动创建）
        """
        if db is None:
            db = DatabaseManager()
            db.initialize()
        
        self.db = db
        
        # 专用加载器（委托模式）
        self.kline_loader = KlineLoader(db)
        self.label_loader = LabelLoader(db)
        
        # 懒加载的表实例（按需创建）
        self._stock_list_table = None
        self._gdp_table = None
        self._lpr_table = None
        self._shibor_table = None
        self._price_indexes_table = None
        self._corporate_finance_table = None
        self._stock_index_indicator_table = None
        self._industry_capital_flow_table = None
    
    # ============ 多进程支持（静态工厂方法）============
    
    @staticmethod
    def create_for_child_process(db_config: Optional[Dict] = None) -> 'DataLoader':
        """
        在子进程中创建DataLoader实例
        
        由于进程隔离，子进程无法共享主进程的数据库连接，
        需要在子进程中重新初始化DatabaseManager。
        
        Args:
            db_config: 数据库配置（可选）
                {
                    'is_verbose': False,
                    'enable_thread_safety': False  # 子进程通常不需要线程安全
                }
        
        Returns:
            DataLoader: 新的DataLoader实例
            
        Example:
            # 在子进程中使用
            def process_stock(stock_id, db_config):
                loader = DataLoader.create_for_child_process(db_config)
                return loader.load_daily_qfq(stock_id)
            
            with ProcessPoolExecutor() as executor:
                futures = [
                    executor.submit(process_stock, sid, {'is_verbose': False})
                    for sid in stock_ids
                ]
        """
        if db_config is None:
            db_config = {'is_verbose': False, 'enable_thread_safety': False}
        
        db = DatabaseManager(**db_config)
        db.initialize()
        return DataLoader(db)
    
    @staticmethod
    def load_klines_in_child(stock_id: str, term: str = 'daily', adjust: str = 'qfq',
                             db_config: Optional[Dict] = None, as_dataframe: bool = False):
        """
        在子进程中加载K线数据（静态方法）
        
        适合多进程场景，每次调用都会创建新的数据库连接。
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            adjust: 复权方式（qfq/hfq/none）
            db_config: 数据库配置
            as_dataframe: 是否返回DataFrame
            
        Returns:
            DataFrame or List[Dict]: K线数据
            
        Example:
            with ProcessPoolExecutor() as executor:
                future = executor.submit(
                    DataLoader.load_klines_in_child,
                    '000001.SZ', 'daily', 'qfq', {'is_verbose': False}
                )
                result = future.result()
        """
        loader = DataLoader.create_for_child_process(db_config)
        return loader.load_klines(stock_id, term, adjust=adjust, as_dataframe=as_dataframe)
    
    # ============ 表实例懒加载（性能优化）============
    
    @property
    def stock_list_table(self):
        if self._stock_list_table is None:
            self._stock_list_table = self.db.get_table_instance('stock_list')
        return self._stock_list_table
    
    # ============ 股票数据服务 ============
    
    # ------------ K线快捷方法（80%场景，零配置）------------
    
    def load_daily_qfq(self, stock_id: str, start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> List[Dict]:
        """
        加载日线前复权数据（最常用，零配置）
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Dict]: 日线前复权数据
            
        Example:
            loader = DataLoader(db)
            records = loader.load_daily_qfq('000001.SZ')  # 最简单！
        """
        return self.kline_loader.load_daily_qfq(stock_id, start_date, end_date)
    
    def load_weekly_qfq(self, stock_id: str, start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> List[Dict]:
        """加载周线前复权数据"""
        return self.kline_loader.load_weekly_qfq(stock_id, start_date, end_date)
    
    def load_monthly_qfq(self, stock_id: str, start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> List[Dict]:
        """加载月线前复权数据"""
        return self.kline_loader.load_monthly_qfq(stock_id, start_date, end_date)
    
    def load_daily_qfq_df(self, stock_id: str, start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """加载日线前复权数据（DataFrame版本，分析用）"""
        return self.kline_loader.load_daily_qfq_df(stock_id, start_date, end_date)
    
    def load_weekly_qfq_df(self, stock_id: str, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """加载周线前复权数据（DataFrame版本）"""
        return self.kline_loader.load_weekly_qfq_df(stock_id, start_date, end_date)
    
    def load_monthly_qfq_df(self, stock_id: str, start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> pd.DataFrame:
        """加载月线前复权数据（DataFrame版本）"""
        return self.kline_loader.load_monthly_qfq_df(stock_id, start_date, end_date)
    
    def load_raw_klines(self, stock_id: str, term: str = 'daily',
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> List[Dict]:
        """加载原始K线数据（不复权，调试用）"""
        return self.kline_loader.load_raw_klines(stock_id, term, start_date, end_date)
    
    def load_raw_klines_df(self, stock_id: str, term: str = 'daily',
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """加载原始K线数据（不复权，DataFrame版本）"""
        return self.kline_loader.load_raw_klines_df(stock_id, term, start_date, end_date)
    
    # ------------ K线完整方法（20%场景，全配置）------------
    
    def load_klines(self, stock_id: str, term: str = 'daily',
                    start_date: Optional[str] = None, end_date: Optional[str] = None,
                    adjust: str = 'qfq', filter_negative: bool = True,
                    as_dataframe: bool = False) -> Union[pd.DataFrame, List[Dict]]:
        """
        加载K线数据（完整方法，支持所有参数）
        
        跨表操作：stock_kline + adj_factor
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust: 复权方式（qfq前复权/hfq后复权/none不复权）
            filter_negative: 是否过滤负值（默认True）
            as_dataframe: 是否返回DataFrame（默认False返回List[Dict]）
            
        Returns:
            DataFrame or List[Dict]: K线数据
            
        Example:
            # 简单用法（推荐）
            records = loader.load_daily_qfq('000001.SZ')
            
            # 完整用法（需要灵活配置）
            records = loader.load_klines(
                stock_id='000001.SZ',
                term='weekly',
                start_date='20200101',
                end_date='20231231',
                adjust='hfq',
                filter_negative=False,
                as_dataframe=True
            )
        """
        return self.kline_loader.load(
            stock_id, term, start_date, end_date, adjust, filter_negative, as_dataframe
        )
    
    def load_stock_klines_data(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载股票K线数据（多个term）
        
        向后兼容方法（analyzer使用）
        
        Args:
            stock_id: 股票代码
            settings: 配置字典，包含terms、adjust、allow_negative_records等
            
        Returns:
            Dict[term, List[Dict]]: 各周期的K线数据
        """
        return self.kline_loader.load_multiple_terms(stock_id, settings)
    
    def load_stock_with_latest_price(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载股票信息及最新价格
        
        跨表：stock_list + stock_kline
        
        Returns:
            Dict: 股票信息 + 最新价格
        """
        # 1. 加载股票信息
        stock_info = self.stock_list_table.load_one(condition="id=%s", params=(stock_id,))
        
        if not stock_info:
            return None
        
        # 2. 加载最新K线
        latest_kline = self.kline_table.get_most_recent_one_by_term(stock_id, 'daily')
        
        # 3. 合并
        if latest_kline:
            stock_info['latest_date'] = latest_kline['date']
            stock_info['latest_close'] = latest_kline['close']
            stock_info['latest_volume'] = latest_kline['volume']
        
        return stock_info
    
    # ============ 股票列表服务 ============
    
    def load_stock_list(self, 
                       filtered: bool = False,
                       industry: str = None,
                       stock_type: str = None,
                       exchange_center: str = None,
                       order_by: str = 'id') -> List[Dict[str, Any]]:
        """
        加载股票列表
        
        Args:
            filtered: 是否使用过滤规则加载（默认True，排除ST、科创板等）
            industry: 按行业过滤（可选）
            stock_type: 按股票类型过滤（可选）
            exchange_center: 按交易所过滤（可选）
            order_by: 排序字段
            
        Returns:
            List[Dict]: 股票列表
            
        示例：
            # 加载过滤后的股票列表（默认，推荐）
            stocks = loader.load_stock_list()
            
            # 加载所有股票（不过滤）
            stocks = loader.load_stock_list(filtered=False)
            
            # 加载特定行业
            stocks = loader.load_stock_list(industry='银行')
            
            # 加载特定交易所
            stocks = loader.load_stock_list(exchange_center='SSE')
        """
        table = self.db.get_table_instance('stock_list')
        
        # 优先使用简单条件过滤（性能更好）
        if industry:
            return table.load_by_industry(industry, order_by)
        elif stock_type:
            return table.load_by_type(stock_type, order_by)
        elif exchange_center:
            return table.load_by_exchange_center(exchange_center, order_by)
        elif filtered:
            # 使用过滤规则（默认行为）
            return table.load_filtered_stock_list(exclude_patterns=None, order_by=order_by)
        else:
            # 加载所有活跃股票（不过滤）
            return table.load_all_active(order_by)
    
    def load_stock_name(self, stock_id: str) -> Optional[str]:
        """
        根据股票ID获取股票名称
        
        Args:
            stock_id: 股票代码 (如 '000001.SZ')
            
        Returns:
            str: 股票名称，如果不存在返回 None
        """
        table = self.db.get_table_instance('stock_list')
        return table.load_name_by_id(stock_id)
    
    def load_stock_names(self, stock_ids: List[str]) -> Dict[str, str]:
        """
        批量获取股票名称
        
        Args:
            stock_ids: 股票代码列表
            
        Returns:
            Dict[str, str]: {stock_id: stock_name} 映射
        """
        table = self.db.get_table_instance('stock_list')
        return table.load_name_by_ids(stock_ids)
    
    # ============ 宏观数据服务 ============
    
    def load_macro_data(self, settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载宏观数据（向后兼容方法）
        
        跨多个表：gdp、lpr、shibor、price_indexes
        
        Args:
            settings: 配置，包含start_date、end_date、GDP、LPR等
            
        Returns:
            Dict: {'GDP': [...], 'LPR': [...], ...}
        """
        macro_data = {}
        
        start_date = settings.get('start_date')
        end_date = settings.get('end_date')
        
        if settings.get('GDP'):
            gdp_table = self.db.get_table_instance('gdp')
            macro_data['GDP'] = gdp_table.load_GDP(start_date, end_date)
        
        if settings.get('LPR'):
            lpr_table = self.db.get_table_instance('lpr')
            macro_data['LPR'] = lpr_table.load_LPR(start_date, end_date)
        
        if settings.get('Shibor'):
            shibor_table = self.db.get_table_instance('shibor')
            macro_data['Shibor'] = shibor_table.load_Shibor(start_date, end_date)
        
        if settings.get('price_indexes'):
            price_indexes_table = self.db.get_table_instance('price_indexes')
            
            requested = settings.get('price_indexes') or []
            if len(requested) == 0:
                requested = ['CPI', 'PPI', 'PMI', 'MoneySupply']
            
            # 统一拉取，再按字段筛选
            all_pi_rows = price_indexes_table.load_price_indexes(start_date, end_date) or []
            
            field_groups = {
                'CPI': ['cpi', 'cpi_yoy', 'cpi_mom'],
                'PPI': ['ppi', 'ppi_yoy', 'ppi_mom'],
                'PMI': ['pmi', 'pmi_l_scale', 'pmi_m_scale', 'pmi_s_scale'],
                'MoneySupply': ['m0', 'm0_yoy', 'm0_mom', 'm1', 'm1_yoy', 'm1_mom', 'm2', 'm2_yoy', 'm2_mom']
            }
            
            for key in requested:
                fields = field_groups.get(key)
                if not fields:
                    continue
                macro_data[key] = [
                    {k: row.get(k) for k in (['date'] + fields) if k in row}
                    for row in all_pi_rows
                ]
        
        return macro_data
    
    # ============ 财务数据服务 ============
    
    def load_corporate_finance_data(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载企业财务数据
        
        Args:
            stock_id: 股票代码
            settings: 配置，包含start_date、end_date、categories
            
        Returns:
            Dict: {'growth': [...], 'profit': [...], ...}
        """
        corporate_finance_data = {}
        
        start_date = settings.get('start_date')
        end_date = settings.get('end_date')
        categories = settings.get('categories') or []
        
        # 允许空数组表示"全部"
        all_categories = [
            'growth', 'profit', 'cashflow', 'solvency', 'operation', 'asset'
        ]
        if isinstance(categories, list) and len(categories) == 0:
            categories = all_categories
        
        if not categories:
            return corporate_finance_data
        
        table = self.db.get_table_instance('corporate_finance')
        
        # 映射类别到加载函数
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
            except Exception as e:
                logger.warning(f"加载财务数据 {cat} 失败: {e}")
                corporate_finance_data[cat] = []
        
        return corporate_finance_data
    
    # ============ 市场数据服务 ============
    
    def load_index_indicators_data(self, settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载指数指标数据（带缓存）
        
        Args:
            settings: 配置，包含start_date、end_date、categories
            
        Returns:
            Dict: {'sh_index': [...], 'sz_index': [...], ...}
        """
        start_date = settings.get('start_date')
        end_date = settings.get('end_date')
        categories = settings.get('categories') or []
        
        # 缓存检查
        cache_key = self._make_cache_key('index_indicators', start_date, end_date, categories)
        cached = self._shared_cache.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)
        
        data = {}
        
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
        
        table = self.db.get_table_instance('stock_index_indicator')
        
        for cat in categories:
            if cat in all_map:
                idx = all_map[cat]
                data[cat] = table.load_index(idx, start_date, end_date) or []
            else:
                # 允许直接传入具体指数代码
                data[cat] = table.load_index(cat, start_date, end_date) or []
        
        # 写入缓存
        self._shared_cache[cache_key] = copy.deepcopy(data)
        return copy.deepcopy(data)
    
    def load_industry_capital_flow_data(self, settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载行业资本流动数据（带缓存）
        
        Args:
            settings: 配置，包含start_date、end_date
            
        Returns:
            Dict: {'all': [...]}
        """
        start_date = settings.get('start_date')
        end_date = settings.get('end_date')
        
        # 缓存检查
        cache_key = self._make_cache_key('industry_capital_flow', start_date, end_date)
        cached = self._shared_cache.get(cache_key)
        if cached is not None:
            return copy.deepcopy(cached)
        
        table = self.db.get_table_instance('industry_capital_flow')
        
        # 构建查询条件
        condition_parts = []
        params = []
        
        if start_date:
            condition_parts.append("date >= %s")
            params.append(start_date)
        
        if end_date:
            condition_parts.append("date <= %s")
            params.append(end_date)
        
        condition = " AND ".join(condition_parts) if condition_parts else "1=1"
        
        records = table.load(condition=condition, params=tuple(params), order_by="date ASC") or []
        result = {'all': records}
        
        # 写入缓存
        self._shared_cache[cache_key] = copy.deepcopy(result)
        return copy.deepcopy(result)
    
    # ============ 聚合数据服务 ============
    
    def prepare_data(self, stock: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备所有需要的数据（聚合方法）
        
        用于策略分析，一次性加载所有需要的数据
        
        Args:
            stock: 股票信息
            settings: 数据设置（包含klines、macro、corporate_finance等配置）
            
        Returns:
            Dict: {
                'klines': {...},
                'macro': {...},
                'corporate_finance': {...},
                ...
            }
        """
        data = {}
        stock_id = stock.get('id')
        
        # 1. 加载K线数据
        klines_settings = settings.get('klines')
        if klines_settings:
            data['klines'] = self.load_stock_klines_data(stock_id, klines_settings)
            
            # 确保返回dict类型
            if not isinstance(data.get('klines'), dict):
                data['klines'] = {}
            
            # 应用技术指标（如果配置）
            if data['klines'] and klines_settings.get('indicators'):
                from app.analyzer.components.indicators import Indicators
                data['klines'] = Indicators.add_indicators(data['klines'], klines_settings['indicators'])
        
        # 2. 加载宏观数据
        macro_settings = settings.get('macro')
        if macro_settings:
            data['macro'] = self.load_macro_data(macro_settings)
        
        # 3. 加载企业财务数据
        corporate_finance_settings = settings.get('corporate_finance')
        if corporate_finance_settings:
            data['corporate_finance'] = self.load_corporate_finance_data(stock_id, corporate_finance_settings)
        
        # 4. 加载指数指标数据
        index_indicators_settings = settings.get('index_indicators')
        if index_indicators_settings:
            data['index_indicators'] = self.load_index_indicators_data(index_indicators_settings)
        
        # 5. 加载行业资金流数据
        industry_capital_flow_settings = settings.get('industry_capital_flow')
        if industry_capital_flow_settings:
            data['industry_capital_flow'] = self.load_industry_capital_flow_data(industry_capital_flow_settings)
        
        return data
    
    # ============ 标签相关方法 ============
    
    def get_stock_labels(self, stock_id: str, target_date: Optional[str] = None) -> List[str]:
        """
        获取股票在指定日期的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            List[str]: 标签ID列表
        """
        return self.label_loader.get_stock_labels(stock_id, target_date)
    
    def save_stock_labels(self, stock_id: str, label_date: str, labels: List[str]):
        """
        保存股票标签
        
        Args:
            stock_id: 股票代码
            label_date: 标签日期 (YYYY-MM-DD)
            labels: 标签ID列表
        """
        self.label_loader.save_stock_labels(stock_id, label_date, labels)
    
    def get_label_definition(self, label_id: str) -> Optional[Dict[str, Any]]:
        """
        获取标签定义
        
        Args:
            label_id: 标签ID
            
        Returns:
            Dict: 标签定义信息
        """
        return self.label_loader.get_label_definition(label_id)
    
    def get_all_label_definitions(self) -> List[Dict[str, Any]]:
        """
        获取所有标签定义
        
        Returns:
            List[Dict]: 所有标签定义列表
        """
        return self.label_loader.get_all_label_definitions()
    
    def batch_calculate_labels(self, stock_ids: List[str], label_date: str, 
                              calculator_func: callable):
        """
        批量计算并保存股票标签
        
        Args:
            stock_ids: 股票代码列表
            label_date: 标签日期 (YYYY-MM-DD)
            calculator_func: 标签计算函数，接收(stock_id, target_date)返回标签列表
        """
        self.label_loader.batch_calculate_labels(stock_ids, label_date, calculator_func)
    
    # ============ 内部工具方法 ============
    
    @staticmethod
    def _make_cache_key(dataset: str, start: Optional[str], end: Optional[str], 
                       categories: Optional[List[str]] = None) -> str:
        """生成缓存键"""
        cats = tuple(sorted(categories)) if isinstance(categories, list) else None
        return f"{dataset}|{start or ''}|{end or ''}|{cats}"

