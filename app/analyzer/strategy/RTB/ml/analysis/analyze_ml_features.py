#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析机器学习特征，优化RTB策略参数
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_features():
    """分析收敛区间ML特征"""
    
    # 读取数据
    df = pd.read_csv('/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/convergence_ml_data.csv')
    
    print("🔍 收敛区间机器学习特征分析")
    print("="*50)
    
    # 基本统计
    print(f"📊 总样本数: {len(df)}")
    print(f"📊 成功案例: {df['is_profitable'].sum()} ({df['is_profitable'].mean()*100:.1f}%)")
    print(f"📊 平均最大涨幅: {df['max_return'].mean():.1f}%")
    print(f"📊 平均最大跌幅: {df['min_return'].mean():.1f}%")
    
    # 分析重要特征
    print("\n🎯 重要特征分析:")
    print("-"*30)
    
    # 1. MA60斜率分析
    print("\n1️⃣ MA60斜率分析:")
    ma60_stats = df.groupby('is_profitable')['ma60_slope'].describe()
    print(ma60_stats)
    
    # 成功和失败的MA60斜率分布
    success_ma60 = df[df['is_profitable']==True]['ma60_slope']
    failure_ma60 = df[df['is_profitable']==False]['ma60_slope']
    
    print(f"   成功案例MA60斜率: 均值={success_ma60.mean():.3f}, 中位数={success_ma60.median():.3f}")
    print(f"   失败案例MA60斜率: 均值={failure_ma60.mean():.3f}, 中位数={failure_ma60.median():.3f}")
    
    # 2. 持续时间分析
    print("\n2️⃣ 收敛区间持续时间分析:")
    duration_stats = df.groupby('is_profitable')['duration_weeks'].describe()
    print(duration_stats)
    
    # 3. MA20斜率分析
    print("\n3️⃣ MA20斜率分析:")
    ma20_stats = df.groupby('is_profitable')['ma20_slope'].describe()
    print(ma20_stats)
    
    # 4. 价格与MA20距离分析
    print("\n4️⃣ 价格与MA20距离分析:")
    close_ma20_stats = df.groupby('is_profitable')['close_to_ma20'].describe()
    print(close_ma20_stats)
    
    # 5. 收敛程度分析
    print("\n5️⃣ 收敛程度分析:")
    convergence_stats = df.groupby('is_profitable')['convergence_ratio'].describe()
    print(convergence_stats)
    
    # 寻找最优阈值
    print("\n🎯 寻找最优特征阈值:")
    print("-"*30)
    
    # MA60斜率阈值
    print("\n📈 MA60斜率阈值分析:")
    for threshold in [0.1, 0.2, 0.3, 0.4, 0.5]:
        mask = df['ma60_slope'] >= threshold
        if mask.sum() > 0:
            win_rate = df[mask]['is_profitable'].mean() * 100
            count = mask.sum()
            print(f"   MA60斜率 >= {threshold}: 胜率={win_rate:.1f}% ({count}个样本)")
    
    # 持续时间阈值
    print("\n⏱️ 持续时间阈值分析:")
    for threshold in [5, 10, 15, 20, 25]:
        mask = df['duration_weeks'] >= threshold
        if mask.sum() > 0:
            win_rate = df[mask]['is_profitable'].mean() * 100
            count = mask.sum()
            print(f"   持续时间 >= {threshold}周: 胜率={win_rate:.1f}% ({count}个样本)")
    
    # MA20斜率阈值
    print("\n📈 MA20斜率阈值分析:")
    for threshold in [0.0, 0.1, 0.2, 0.3]:
        mask = df['ma20_slope'] >= threshold
        if mask.sum() > 0:
            win_rate = df[mask]['is_profitable'].mean() * 100
            count = mask.sum()
            print(f"   MA20斜率 >= {threshold}: 胜率={win_rate:.1f}% ({count}个样本)")
    
    # 多特征组合分析
    print("\n🎯 多特征组合分析:")
    print("-"*30)
    
    # 组合1: MA60斜率 > 0.2 AND 持续时间 > 10周
    mask1 = (df['ma60_slope'] >= 0.2) & (df['duration_weeks'] >= 10)
    if mask1.sum() > 0:
        win_rate1 = df[mask1]['is_profitable'].mean() * 100
        avg_return1 = df[mask1]['max_return'].mean()
        print(f"   MA60斜率>=0.2 AND 持续时间>=10周: 胜率={win_rate1:.1f}%, 平均涨幅={avg_return1:.1f}% ({mask1.sum()}个样本)")
    
    # 组合2: MA60斜率 > 0.3 AND MA20斜率 > 0.1
    mask2 = (df['ma60_slope'] >= 0.3) & (df['ma20_slope'] >= 0.1)
    if mask2.sum() > 0:
        win_rate2 = df[mask2]['is_profitable'].mean() * 100
        avg_return2 = df[mask2]['max_return'].mean()
        print(f"   MA60斜率>=0.3 AND MA20斜率>=0.1: 胜率={win_rate2:.1f}%, 平均涨幅={avg_return2:.1f}% ({mask2.sum()}个样本)")
    
    # 组合3: 收敛程度 < 0.07 AND 价格低于MA20
    mask3 = (df['convergence_ratio'] < 0.07) & (df['close_to_ma20'] < 0)
    if mask3.sum() > 0:
        win_rate3 = df[mask3]['is_profitable'].mean() * 100
        avg_return3 = df[mask3]['max_return'].mean()
        print(f"   收敛程度<0.07 AND 价格低于MA20: 胜率={win_rate3:.1f}%, 平均涨幅={avg_return3:.1f}% ({mask3.sum()}个样本)")
    
    # 最优参数建议
    print("\n💡 最优参数建议:")
    print("-"*30)
    
    # 基于分析结果提出建议
    print("基于机器学习分析，建议的RTB策略优化参数:")
    print("1. MA60斜率 >= 0.3 (长期趋势向上)")
    print("2. 收敛区间持续时间 >= 10周 (充分整理)")
    print("3. MA20斜率 >= 0.1 (短期趋势向上)")
    print("4. 收敛程度 < 0.07 (均线充分收敛)")
    print("5. 价格接近或低于MA20 (相对低位)")
    
    # 验证最优组合
    optimal_mask = (
        (df['ma60_slope'] >= 0.3) & 
        (df['duration_weeks'] >= 10) & 
        (df['ma20_slope'] >= 0.1) & 
        (df['convergence_ratio'] < 0.07)
    )
    
    if optimal_mask.sum() > 0:
        optimal_win_rate = df[optimal_mask]['is_profitable'].mean() * 100
        optimal_avg_return = df[optimal_mask]['max_return'].mean()
        optimal_count = optimal_mask.sum()
        print(f"\n🎯 最优组合验证:")
        print(f"   满足所有条件的样本: {optimal_count}个")
        print(f"   胜率: {optimal_win_rate:.1f}%")
        print(f"   平均涨幅: {optimal_avg_return:.1f}%")
    else:
        print("\n⚠️ 没有样本满足所有最优条件，建议适当放宽条件")
        
        # 放宽条件测试
        relaxed_mask = (
            (df['ma60_slope'] >= 0.2) & 
            (df['duration_weeks'] >= 8) & 
            (df['ma20_slope'] >= 0.05) & 
            (df['convergence_ratio'] < 0.08)
        )
        
        if relaxed_mask.sum() > 0:
            relaxed_win_rate = df[relaxed_mask]['is_profitable'].mean() * 100
            relaxed_avg_return = df[relaxed_mask]['max_return'].mean()
            relaxed_count = relaxed_mask.sum()
            print(f"\n🎯 放宽条件组合:")
            print(f"   满足放宽条件的样本: {relaxed_count}个")
            print(f"   胜率: {relaxed_win_rate:.1f}%")
            print(f"   平均涨幅: {relaxed_avg_return:.1f}%")

if __name__ == "__main__":
    analyze_features()
