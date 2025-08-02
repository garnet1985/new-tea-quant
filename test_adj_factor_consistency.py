#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from loguru import logger

def test_adj_factor_consistency():
    print("=" * 60)
    print("验证复权因子一致性对策略的影响")
    print("=" * 60)
    
    # 模拟历史价格数据（不复权）
    dates = pd.date_range('2020-01-01', '2020-12-31', freq='D')
    np.random.seed(42)
    
    # 生成模拟的不复权价格序列
    raw_prices = []
    price = 10.0
    for _ in range(len(dates)):
        # 模拟价格变化
        change = np.random.normal(0, 0.02)  # 2%的日波动
        price = price * (1 + change)
        raw_prices.append(price)
    
    # 创建模拟数据
    data = pd.DataFrame({
        'date': dates,
        'raw_price': raw_prices
    })
    
    print(f"\n1. 原始不复权价格数据:")
    print(f"起始价格: {data['raw_price'].iloc[0]:.4f}")
    print(f"结束价格: {data['raw_price'].iloc[-1]:.4f}")
    print(f"总涨跌幅: {(data['raw_price'].iloc[-1] / data['raw_price'].iloc[0] - 1) * 100:.2f}%")
    
    # 模拟不同的复权因子
    factors = [1.0, 2.0, 5.0, 10.0, 100.0]
    
    print(f"\n2. 使用不同复权因子的结果对比:")
    
    for factor in factors:
        # 计算复权价格
        data[f'adj_price_{factor}'] = data['raw_price'] * factor
        
        # 计算技术指标（以移动平均为例）
        data[f'ma_5_{factor}'] = data[f'adj_price_{factor}'].rolling(5).mean()
        data[f'ma_20_{factor}'] = data[f'adj_price_{factor}'].rolling(20).mean()
        
        # 计算相对指标
        data[f'ma_ratio_{factor}'] = data[f'adj_price_{factor}'] / data[f'ma_20_{factor}']
        
        # 计算涨跌幅
        data[f'return_{factor}'] = data[f'adj_price_{factor}'].pct_change()
        
        print(f"\n复权因子: {factor}")
        print(f"  复权后起始价格: {data[f'adj_price_{factor}'].iloc[0]:.4f}")
        print(f"  复权后结束价格: {data[f'adj_price_{factor}'].iloc[-1]:.4f}")
        print(f"  复权后总涨跌幅: {(data[f'adj_price_{factor}'].iloc[-1] / data[f'adj_price_{factor}'].iloc[0] - 1) * 100:.2f}%")
        
        # 检查相对关系
        latest_ma_ratio = data[f'ma_ratio_{factor}'].iloc[-1]
        print(f"  最新价格/20日均价比率: {latest_ma_ratio:.4f}")
    
    # 验证相对关系的一致性
    print(f"\n3. 验证相对关系的一致性:")
    
    # 检查不同复权因子下的相对指标是否一致
    base_factor = 1.0
    for factor in factors[1:]:
        # 比较价格/均价比率
        ratio_diff = abs(data[f'ma_ratio_{factor}'].iloc[-1] - data[f'ma_ratio_{base_factor}'].iloc[-1])
        print(f"  复权因子{base_factor} vs {factor}的价格/均价比率差异: {ratio_diff:.6f}")
        
        # 比较涨跌幅
        return_diff = abs(data[f'return_{factor}'].iloc[-1] - data[f'return_{base_factor}'].iloc[-1])
        print(f"  复权因子{base_factor} vs {factor}的日涨跌幅差异: {return_diff:.6f}")
    
    # 模拟策略信号
    print(f"\n4. 模拟策略信号一致性:")
    
    # 定义简单的策略：价格低于20日均价的90%时买入
    threshold = 0.9
    
    for factor in factors:
        buy_signals = data[f'ma_ratio_{factor}'] < threshold
        signal_count = buy_signals.sum()
        latest_signal = buy_signals.iloc[-1]
        
        print(f"  复权因子{factor}: 买入信号次数={signal_count}, 最新信号={'是' if latest_signal else '否'}")
    
    # 验证历史低点分析
    print(f"\n5. 历史低点分析一致性:")
    
    for factor in factors:
        # 计算历史低点（过去30天的最低点）
        data[f'low_30_{factor}'] = data[f'adj_price_{factor}'].rolling(30).min()
        current_price = data[f'adj_price_{factor}'].iloc[-1]
        low_30 = data[f'low_30_{factor}'].iloc[-1]
        
        # 计算当前价格相对于30日低点的位置
        low_ratio = current_price / low_30
        
        print(f"  复权因子{factor}: 当前价格={current_price:.4f}, 30日低点={low_30:.4f}, 低点比率={low_ratio:.4f}")
    
    print("\n" + "=" * 60)
    print("结论：只要使用一致的复权因子，相对关系和技术分析结果都是一致的")
    print("=" * 60)

if __name__ == "__main__":
    test_adj_factor_consistency() 