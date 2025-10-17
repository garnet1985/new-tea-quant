"""
K线数据加载器

专门负责股票K线数据的加载、复权、过滤等操作
"""
from typing import List, Dict, Any, Optional, Union
import pandas as pd
from loguru import logger

from ..helpers import AdjustmentHelper, FilteringHelper


class KlineLoader:
    """K线数据加载器"""
    
    def __init__(self, db):
        """
        初始化K线加载器
        
        Args:
            db: DatabaseManager实例
        """
        self.db = db
        self.kline_table = db.get_table_instance('stock_kline')
        self.adj_factor_table = db.get_table_instance('adj_factor')
    
    # ============ 快捷方法（最常用，80%场景）============
    
    def load_daily_qfq(self, stock_id: str, start_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> List[Dict]:
        """
        加载日线前复权数据（最常用）
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Dict]: 日线前复权数据
        """
        return self.load(stock_id, term='daily', start_date=start_date, 
                        end_date=end_date, adjust='qfq', as_dataframe=False)
    
    def load_weekly_qfq(self, stock_id: str, start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> List[Dict]:
        """
        加载周线前复权数据
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Dict]: 周线前复权数据
        """
        return self.load(stock_id, term='weekly', start_date=start_date,
                        end_date=end_date, adjust='qfq', as_dataframe=False)
    
    def load_monthly_qfq(self, stock_id: str, start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> List[Dict]:
        """
        加载月线前复权数据
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Dict]: 月线前复权数据
        """
        return self.load(stock_id, term='monthly', start_date=start_date,
                        end_date=end_date, adjust='qfq', as_dataframe=False)
    
    # ============ DataFrame版本（分析用）============
    
    def load_daily_qfq_df(self, stock_id: str, start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        加载日线前复权数据（DataFrame版本）
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            DataFrame: 日线前复权数据
        """
        return self.load(stock_id, term='daily', start_date=start_date,
                        end_date=end_date, adjust='qfq', as_dataframe=True)
    
    def load_weekly_qfq_df(self, stock_id: str, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """
        加载周线前复权数据（DataFrame版本）
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            DataFrame: 周线前复权数据
        """
        return self.load(stock_id, term='weekly', start_date=start_date,
                        end_date=end_date, adjust='qfq', as_dataframe=True)
    
    def load_monthly_qfq_df(self, stock_id: str, start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> pd.DataFrame:
        """
        加载月线前复权数据（DataFrame版本）
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            DataFrame: 月线前复权数据
        """
        return self.load(stock_id, term='monthly', start_date=start_date,
                        end_date=end_date, adjust='qfq', as_dataframe=True)
    
    # ============ 不复权版本（调试/对比用）============
    
    def load_raw_klines(self, stock_id: str, term: str = 'daily',
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> List[Dict]:
        """
        加载原始K线数据（不复权）
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            List[Dict]: 原始K线数据
        """
        return self.load(stock_id, term=term, start_date=start_date,
                        end_date=end_date, adjust='none', as_dataframe=False)
    
    def load_raw_klines_df(self, stock_id: str, term: str = 'daily',
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        加载原始K线数据（不复权，DataFrame版本）
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            DataFrame: 原始K线数据
        """
        return self.load(stock_id, term=term, start_date=start_date,
                        end_date=end_date, adjust='none', as_dataframe=True)
    
    # ============ 完整方法（灵活需求，20%场景）============
    
    def load(self, stock_id: str, term: str = 'daily', 
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
            return self._load_as_dataframe(
                condition, tuple(params), stock_id, adjust, filter_negative
            )
        else:
            return self._load_as_list(
                stock_id, term, adjust, filter_negative
            )
    
    def load_multiple_terms(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """
        加载多个周期的K线数据
        
        向后兼容方法（analyzer使用）
        
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
        
        kline_data = {}
        
        for term in settings.get('terms', []):
            records = self.load(
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
    
    # ============ 内部方法 ============
    
    def _load_as_dataframe(self, condition: str, params: tuple, stock_id: str,
                          adjust: str, filter_negative: bool) -> pd.DataFrame:
        """加载为DataFrame"""
        df = self.kline_table.load_many_df(
            condition=condition,
            params=params,
            order_by='date'
        )
        
        if df.empty:
            return df
        
        # 应用复权
        if adjust != 'none':
            df_factors = self.adj_factor_table.get_stock_factors_df(stock_id)
            if not df_factors.empty:
                df = AdjustmentHelper.apply_df(df, df_factors, adjust)
        
        # 过滤负值
        if filter_negative:
            df = FilteringHelper.filter_negative_df(df)
        
        return df
    
    def _load_as_list(self, stock_id: str, term: str, adjust: str,
                     filter_negative: bool) -> List[Dict]:
        """加载为List[Dict]"""
        records = self.kline_table.get_all_k_lines_by_term(stock_id, term)
        
        if not records:
            return []
        
        # 应用复权
        if adjust in ['qfq', 'hfq']:
            factors = self.adj_factor_table.get_stock_factors(stock_id)
            if factors:
                records = AdjustmentHelper.apply_list(records, factors, adjust)
        
        # 过滤负值
        if filter_negative:
            records = FilteringHelper.filter_negative_records(records)
        
        return records
