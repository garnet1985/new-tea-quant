#!/usr/bin/env python3
"""
数据加载服务 - 全局数据服务工具类

位置：app/data_loader/（应用层，与analyzer、data_source并列）

职责：
- 提供各种业务需求的数据服务
- 处理跨表操作和数据聚合
- 封装数据处理逻辑（复权、过滤、指标计算等）

设计：
- 统一的DataLoader类（包含stock、macro等所有数据服务）
- 按需扩展（未来如果方法太多可以拆分文件）
- 工具类风格（不是Repository模式，不需要基类）
"""
from typing import Dict, List, Any, Optional
import copy
import pandas as pd
from loguru import logger
from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_service import DataSourceService


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
        
        # 懒加载的表实例（按需创建）
        self._kline_table = None
        self._adj_factor_table = None
        self._stock_list_table = None
        self._gdp_table = None
        self._lpr_table = None
        self._shibor_table = None
        self._price_indexes_table = None
        self._corporate_finance_table = None
        self._stock_index_indicator_table = None
        self._industry_capital_flow_table = None
    
    # ============ 表实例懒加载（性能优化）============
    
    @property
    def kline_table(self):
        if self._kline_table is None:
            self._kline_table = self.db.get_table_instance('stock_kline')
        return self._kline_table
    
    @property
    def adj_factor_table(self):
        if self._adj_factor_table is None:
            self._adj_factor_table = self.db.get_table_instance('adj_factor')
        return self._adj_factor_table
    
    @property
    def stock_list_table(self):
        if self._stock_list_table is None:
            self._stock_list_table = self.db.get_table_instance('stock_list')
        return self._stock_list_table
    
    # ============ 股票数据服务 ============
    
    def load_klines(self, 
                    stock_id: str,
                    term: str = 'daily',
                    start_date: str = None,
                    end_date: str = None,
                    adjust: str = 'qfq',
                    as_dataframe: bool = False,
                    filter_negative: bool = True) -> Any:
        """
        加载K线数据（最常用方法）
        
        跨表操作：stock_kline + adj_factor
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust: 复权方式（qfq前复权/hfq后复权/none不复权）
            as_dataframe: 是否返回DataFrame（默认False返回List[Dict]）
            filter_negative: 是否过滤负值（默认True）
            
        Returns:
            DataFrame or List[Dict]: K线数据
        """
        # 1. 构建查询条件
        condition = "id=%s AND term=%s"
        params = [stock_id, term]
        
        if start_date:
            condition += " AND date>=%s"
            params.append(start_date)
        
        if end_date:
            condition += " AND date<=%s"
            params.append(end_date)
        
        # 2. 加载K线
        if as_dataframe:
            df = self.kline_table.load_many_df(
                condition=condition,
                params=tuple(params),
                order_by='date'
            )
            
            if df.empty:
                return df
            
            # 应用复权（使用优化的DataFrame方法）
            if adjust != 'none':
                # 直接获取DataFrame格式的复权因子（已排序，无需转换）
                df_factors = self.adj_factor_table.get_stock_factors_df(stock_id)
                if not df_factors.empty:
                    df = self._apply_adjustment_df(df, df_factors, adjust)
            
            # 过滤负值（DataFrame方法，一行搞定）
            if filter_negative:
                df = df[df['close'] > 0].reset_index(drop=True)
            
            return df
        else:
            # 返回List[Dict]（向后兼容，使用for循环保证性能）
            records = self.kline_table.get_all_k_lines_by_term(stock_id, term)
            
            if not records:
                return []
            
            # 应用复权（使用内部方法，不依赖DataSourceService）
            if adjust in ['qfq', 'hfq']:
                factors = self.adj_factor_table.get_stock_factors(stock_id)
                if factors:
                    records = self._apply_adjustment_list(records, factors, adjust)
            
            # 过滤负值（使用内部方法）
            if filter_negative:
                records = self._filter_negative_records(records)
            
            return records
    
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
        min_required_base_records = settings.get('min_required_base_records', 0)
        min_required_kline_term = settings.get('base_term')
        adjust = settings.get('adjust', 'qfq')
        allow_negative_records = settings.get('allow_negative_records', False)
        
        kline_data = {}
        
        for term in settings.get('terms', []):
            records = self.load_klines(
                stock_id=stock_id,
                term=term,
                adjust=adjust,
                as_dataframe=False,
                filter_negative=not allow_negative_records
            )
            kline_data[term] = records
        
        # 检查最小记录数要求
        if min_required_base_records > 0:
            base_records = kline_data.get(min_required_kline_term, [])
            if len(base_records) < min_required_base_records:
                # 返回包含所有请求term的空列表
                return {term: [] for term in settings.get('terms', [])}
        
        return kline_data
    
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
                'CPI': ['CPI', 'CPI_yoy', 'CPI_mom'],
                'PPI': ['PPI', 'PPI_yoy', 'PPI_mom'],
                'PMI': ['PMI', 'PMI_l_scale', 'PMI_m_scale', 'PMI_s_scale'],
                'MoneySupply': ['M0', 'M0_yoy', 'M0_mom', 'M1', 'M1_yoy', 'M1_mom', 'M2', 'M2_yoy', 'M2_mom']
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
    
    # ============ 内部工具方法 ============
    
    @staticmethod
    def _apply_adjustment_list(records: List[Dict], factors: List[Dict], adjust_type: str) -> List[Dict]:
        """
        应用复权计算（List版本，for循环）
        
        用于List[Dict]格式的数据，性能优于DataFrame（~0.006秒 vs ~0.1秒）
        
        Args:
            records: K线数据列表
            factors: 复权因子列表
            adjust_type: 'qfq'前复权 或 'hfq'后复权
            
        Returns:
            List[Dict]: 复权后的K线数据（原地修改）
        """
        if not records or not factors:
            return records
        
        # 确保因子按日期升序
        sorted_factors = sorted(factors, key=lambda x: x['date'])
        
        # 确定使用哪个因子字段
        factor_field = 'qfq' if adjust_type == 'qfq' else 'hfq'
        
        # 获取默认因子
        default_factor = sorted_factors[0].get(factor_field, 1.0) if sorted_factors else 1.0
        
        # 处理每条K线
        for k_line in records:
            # 保存原始值
            k_line['raw'] = {
                'open': k_line.get('open'),
                'close': k_line.get('close'),
                'highest': k_line.get('highest'),
                'lowest': k_line.get('lowest')
            }
            
            # 获取当前K线的日期
            current_date = k_line.get('date')
            if not current_date:
                continue
            
            # 查找对应的复权因子（向后查找）
            factor_value = default_factor
            for factor in sorted_factors:
                if factor['date'] <= current_date:
                    factor_value = factor.get(factor_field, factor_value)
                else:
                    break
            
            # 计算复权价格
            if factor_value:
                for price_col in ['open', 'close', 'highest', 'lowest']:
                    if k_line['raw'][price_col] is not None:
                        k_line[price_col] = k_line['raw'][price_col] * factor_value
        
        return records
    
    @staticmethod
    def _filter_negative_records(records: List[Dict]) -> List[Dict]:
        """
        过滤负值记录
        
        Args:
            records: K线数据列表
            
        Returns:
            List[Dict]: 过滤后的数据
        """
        if not records:
            return []
        
        return [r for r in records if r.get('close', 0) and r.get('close') > 0]
    
    def _apply_adjustment_df(self, df: pd.DataFrame, df_factors: pd.DataFrame, adjust_type: str) -> pd.DataFrame:
        """
        应用复权计算（DataFrame优化版本）
        
        优化：
        - 接受DataFrame格式的factors（避免dict→DataFrame转换）
        - 数据库已排序，不需要再sort（避免排序开销）
        - 使用merge_asof自动匹配复权因子
        
        Args:
            df: K线DataFrame，包含date、open、close、highest、lowest列（已按date排序）
            df_factors: 复权因子DataFrame，包含date和qfq/hfq字段（已按date排序）
            adjust_type: 'qfq'前复权 或 'hfq'后复权
            
        Returns:
            pd.DataFrame: 复权后的K线数据
        """
        if df_factors.empty:
            logger.debug("复权因子为空，返回原始数据")
            return df
        
        # 1. 确定使用哪个复权因子字段
        factor_field = 'qfq' if adjust_type == 'qfq' else 'hfq'
        
        if factor_field not in df_factors.columns:
            logger.warning(f"复权因子中没有{factor_field}字段，返回原始数据")
            return df
        
        # 2. 准备复权因子（重命名，避免冲突）
        df_factor = df_factors[['date', factor_field]].copy()
        df_factor = df_factor.rename(columns={factor_field: 'factor'})
        
        # 3. 将date转换为数值类型（merge_asof要求）
        df = df.copy()  # 避免修改原DataFrame
        df['date_int'] = df['date'].astype(str).astype(int)
        df_factor['date_int'] = df_factor['date'].astype(str).astype(int)
        
        # 4. 保存原始价格（用于回溯分析）
        price_columns = ['open', 'close', 'highest', 'lowest']
        for col in price_columns:
            if col in df.columns:
                df[f'raw_{col}'] = df[col]
        
        # 5. 使用merge_asof匹配复权因子
        # 注意：df和df_factor都来自数据库，已按date排序，不需要sort
        merged = pd.merge_asof(
            df,  # 已排序（数据库order_by='date'）
            df_factor[['date_int', 'factor']],  # 已排序（数据库order_by='date ASC'）
            on='date_int',
            direction='backward'  # 向后查找：使用小于等于当前日期的最近因子
        )
        
        # 6. 向量化计算复权价格（批量乘法）
        for col in price_columns:
            if col in merged.columns and 'factor' in merged.columns:
                merged[col] = merged[col] * merged['factor']
        
        # 7. 删除临时列
        merged = merged.drop(columns=['date_int', 'factor'])
        
        return merged
    
    @staticmethod
    def _make_cache_key(dataset: str, start: Optional[str], end: Optional[str], 
                       categories: Optional[List[str]] = None) -> str:
        """生成缓存键"""
        cats = tuple(sorted(categories)) if isinstance(categories, list) else None
        return f"{dataset}|{start or ''}|{end or ''}|{cats}"

