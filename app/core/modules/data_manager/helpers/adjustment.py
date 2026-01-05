"""
复权计算工具

提供List和DataFrame两种格式的复权计算方法
"""
from typing import List, Dict
import pandas as pd
from loguru import logger


class AdjustmentHelper:
    """复权计算辅助类"""
    
    @staticmethod
    def apply_list(records: List[Dict], factors: List[Dict], adjust_type: str) -> List[Dict]:
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
    def apply_df(df: pd.DataFrame, df_factors: pd.DataFrame, adjust_type: str) -> pd.DataFrame:
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
