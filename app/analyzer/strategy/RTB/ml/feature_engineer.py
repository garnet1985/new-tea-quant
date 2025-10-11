#!/usr/bin/env python3
"""
RTB 策略 - 特征工程模块
提取所有用于ML训练的特征
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class RTBFeatureEngineer:
    """RTB策略特征工程师"""
    
    def __init__(self):
        """初始化"""
        self.feature_names = []
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从K线数据提取所有特征
        
        Args:
            df: K线DataFrame，必须包含: date, open, close, highest, lowest, volume
        
        Returns:
            带特征的DataFrame
        """
        df = df.copy()
        
        # ========================================
        # 基础均线
        # ========================================
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # ========================================
        # 核心特征（来自requirements）
        # ========================================
        
        # 1. 均线收敛度
        ma_array = df[['ma5', 'ma10', 'ma20', 'ma60']].values
        df['ma_std'] = np.std(ma_array, axis=1) / df['close']
        df['ma_bandwidth'] = (ma_array.max(axis=1) - ma_array.min(axis=1)) / df['close']
        
        # 2. 价格位置（震荡区）
        high_20d = df['highest'].rolling(20).max()
        low_20d = df['lowest'].rolling(20).min()
        df['position_20d'] = (df['close'] - low_20d) / (high_20d - low_20d)
        
        high_60d = df['highest'].rolling(60).max()
        low_60d = df['lowest'].rolling(60).min()
        df['position_60d'] = (df['close'] - low_60d) / (high_60d - low_60d)
        
        # 3. 趋势斜率
        df['ma60_20d_ago'] = df['ma60'].shift(20)
        df['ma60slope'] = (df['ma60'] - df['ma60_20d_ago']) / df['ma60_20d_ago']
        
        df['ma20_10d_ago'] = df['ma20'].shift(10)
        df['ma20slope'] = (df['ma20'] - df['ma20_10d_ago']) / df['ma20_10d_ago']
        
        # ========================================
        # 额外特征（ML可能用到）
        # ========================================
        
        # 4. 前期跌幅
        df['drawdown_20d'] = (high_20d - df['close']) / high_20d
        df['drawdown_60d'] = (high_60d - df['close']) / high_60d
        
        # 5. 价格动量
        df['return_5d'] = df['close'].pct_change(5)
        df['return_10d'] = df['close'].pct_change(10)
        df['return_20d'] = df['close'].pct_change(20)
        
        # 6. 波动率
        returns = df['close'].pct_change()
        df['volatility_5d'] = returns.rolling(5).std()
        df['volatility_20d'] = returns.rolling(20).std()
        df['volatility_60d'] = returns.rolling(60).std()
        
        # 7. 成交量特征
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        # 8. 价格相对均线
        df['close_to_ma5'] = (df['close'] - df['ma5']) / df['ma5']
        df['close_to_ma20'] = (df['close'] - df['ma20']) / df['ma20']
        df['close_to_ma60'] = (df['close'] - df['ma60']) / df['ma60']
        
        # 9. 均线排列
        df['ma5_above_ma20'] = (df['ma5'] > df['ma20']).astype(int)
        df['ma20_above_ma60'] = (df['ma20'] > df['ma60']).astype(int)
        df['price_above_ma60'] = (df['close'] > df['ma60']).astype(int)
        
        # 10. 震荡幅度
        df['amplitude_20d'] = (high_20d - low_20d) / df['close']
        
        return df
    
    def get_feature_columns(self) -> List[str]:
        """
        获取所有特征列名（用于ML训练）
        
        Returns:
            特征列名列表
        """
        return [
            # 核心特征
            'ma_std',
            'ma_bandwidth',
            'position_20d',
            'position_60d',
            'ma60slope',
            'ma20slope',
            
            # 前期跌幅
            'drawdown_20d',
            'drawdown_60d',
            
            # 价格动量
            'return_5d',
            'return_10d',
            'return_20d',
            
            # 波动率
            'volatility_5d',
            'volatility_20d',
            'volatility_60d',
            
            # 成交量
            'volume_ratio',
            
            # 价格相对均线
            'close_to_ma5',
            'close_to_ma20',
            'close_to_ma60',
            
            # 均线排列
            'ma5_above_ma20',
            'ma20_above_ma60',
            'price_above_ma60',
            
            # 震荡幅度
            'amplitude_20d',
        ]
    
    def create_labels(self, df: pd.DataFrame, holding_period=120) -> pd.DataFrame:
        """
        创建训练标签
        
        注意：这里只计算"潜在最大收益"，用于训练
        实际交易收益需要考虑止损止盈
        
        Args:
            df: 带特征的DataFrame
            holding_period: 持有期（天）
        
        Returns:
            带标签的DataFrame
        """
        df = df.copy()
        
        # 计算未来最大收益（用于训练）
        future_high = df['highest'].shift(-1).rolling(holding_period).max()
        df['future_max_return'] = (future_high - df['close']) / df['close']
        
        # 多层标签
        df['label_10'] = (df['future_max_return'] >= 0.10).astype(int)
        df['label_15'] = (df['future_max_return'] >= 0.15).astype(int)
        df['label_20'] = (df['future_max_return'] >= 0.20).astype(int)
        df['label_30'] = (df['future_max_return'] >= 0.30).astype(int)
        
        return df
    
    def filter_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据requirements定义过滤出信号
        
        Args:
            df: 带特征的DataFrame
        
        Returns:
            符合条件的信号
        """
        signals = df[
            (df['ma_std'] < 0.03) &
            (df['position_20d'] < 0.30) &
            (df['ma60slope'] > -0.176) &
            (df['ma60slope'] < 0.176)
        ].copy()
        
        return signals
    
    def prepare_training_data(self, df: pd.DataFrame, 
                            deduplicate: bool = True,
                            cooling_period: int = 120) -> pd.DataFrame:
        """
        准备ML训练数据
        
        Args:
            df: 原始K线数据
            deduplicate: 是否去重
            cooling_period: 去重冷却期
        
        Returns:
            训练数据DataFrame
        """
        # 1. 提取特征
        df = self.extract_features(df)
        
        # 2. 创建标签
        df = self.create_labels(df, holding_period=120)
        
        # 3. 过滤信号
        signals = self.filter_signals(df)
        
        # 4. 去重（如果需要）
        if deduplicate:
            signals = self._deduplicate_signals(signals, cooling_period)
        
        # 5. 删除无效行
        signals = signals.dropna(subset=['future_max_return'])
        
        return signals
    
    def _deduplicate_signals(self, signals: pd.DataFrame, 
                            cooling_period: int = 120) -> pd.DataFrame:
        """
        信号去重
        """
        if len(signals) == 0 or 'stock_id' not in signals.columns:
            return signals
        
        signals = signals.sort_values(['stock_id', 'date']).reset_index(drop=True)
        
        deduped_indices = []
        last_buy_date = {}
        
        for idx, row in signals.iterrows():
            stock_id = row['stock_id']
            current_date = row['date']
            
            if stock_id in last_buy_date:
                days_since_last_buy = (current_date - last_buy_date[stock_id]).days
                
                if days_since_last_buy < cooling_period:
                    continue
            
            deduped_indices.append(idx)
            last_buy_date[stock_id] = current_date
        
        return signals.loc[deduped_indices].reset_index(drop=True)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    print("RTB Feature Engineer - 使用示例")
    print("="*60)
    
    # 创建特征工程师
    engineer = RTBFeatureEngineer()
    
    # 获取特征列表
    features = engineer.get_feature_columns()
    print(f"\n总共 {len(features)} 个特征:")
    for i, feature in enumerate(features, 1):
        print(f"  {i:2d}. {feature}")
    
    print("\n特征工程器准备完成！")
    print("可以用于批量提取训练数据")

