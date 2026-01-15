"""
数据过滤工具

提供数据清洗和过滤功能
"""
from typing import List, Dict
import pandas as pd


class FilteringHelper:
    """数据过滤辅助类"""
    
    @staticmethod
    def filter_negative_records(records: List[Dict]) -> List[Dict]:
        """
        过滤负值记录（List版本）
        
        Args:
            records: K线数据列表
            
        Returns:
            List[Dict]: 过滤后的数据
        """
        if not records:
            return []
        
        return [r for r in records if r.get('close', 0) and r.get('close') > 0]
    
    @staticmethod
    def filter_negative_df(df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤负值记录（DataFrame版本）
        
        Args:
            df: K线DataFrame
            
        Returns:
            pd.DataFrame: 过滤后的数据
        """
        if df.empty:
            return df
        
        return df[df['close'] > 0].reset_index(drop=True)
