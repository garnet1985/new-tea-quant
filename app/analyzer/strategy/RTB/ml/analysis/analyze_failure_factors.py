#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反向研究失败案例，找出导致收敛后下跌的关键因子
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import xgboost as xgb

def analyze_failure_factors():
    """分析失败案例的关键因子"""
    
    print("🔍 反向研究：为什么6成收敛案例会失败？")
    print("="*60)
    
    # 读取包含成交量特征的数据
    df = pd.read_csv('/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/convergence_with_volume_data.csv')
    
    print(f"📊 总样本数: {len(df)}")
    print(f"📊 成功案例: {df['is_profitable'].sum()} ({df['is_profitable'].mean()*100:.1f}%)")
    print(f"📊 失败案例: {(~df['is_profitable']).sum()} ({(~df['is_profitable']).mean()*100:.1f}%)")
    
    # 分离成功和失败案例
    success_cases = df[df['is_profitable'] == True]
    failure_cases = df[df['is_profitable'] == False]
    
    print(f"\n📊 成功案例样本: {len(success_cases)}")
    print(f"📊 失败案例样本: {len(failure_cases)}")
    
    # 定义所有特征
    feature_columns = [
        'duration_weeks', 'price_change_pct', 'price_range_pct', 'convergence_ratio',
        'ma20_slope', 'ma60_slope', 'position_in_range', 'close_to_ma20',
        'volume_ratio', 'amount_ratio', 'volume_trend', 'amount_trend', 'avg_volume', 'avg_amount'
    ]
    
    print(f"\n🎯 失败案例特征分析:")
    print("-"*40)
    
    # 1. 基础统计对比
    print("1️⃣ 基础统计对比:")
    comparison_stats = []
    
    for feature in feature_columns:
        success_mean = success_cases[feature].mean()
        failure_mean = failure_cases[feature].mean()
        success_std = success_cases[feature].std()
        failure_std = failure_cases[feature].std()
        
        # 计算差异程度
        if success_std > 0 and failure_std > 0:
            diff_ratio = abs(success_mean - failure_mean) / ((success_std + failure_std) / 2)
        else:
            diff_ratio = 0
        
        comparison_stats.append({
            'feature': feature,
            'success_mean': success_mean,
            'failure_mean': failure_mean,
            'success_std': success_std,
            'failure_std': failure_std,
            'diff_ratio': diff_ratio,
            'difference': success_mean - failure_mean
        })
    
    # 按差异程度排序
    comparison_stats.sort(key=lambda x: x['diff_ratio'], reverse=True)
    
    print("📊 特征差异排序 (成功 vs 失败):")
    for i, stat in enumerate(comparison_stats[:10]):
        print(f"  {i+1:2d}. {stat['feature']}:")
        print(f"      成功: {stat['success_mean']:.3f} ± {stat['success_std']:.3f}")
        print(f"      失败: {stat['failure_mean']:.3f} ± {stat['failure_std']:.3f}")
        print(f"      差异: {stat['difference']:.3f} (差异度: {stat['diff_ratio']:.3f})")
        print()
    
    # 2. 失败案例的典型特征模式
    print("2️⃣ 失败案例的典型特征模式:")
    print("-"*40)
    
    # 分析失败案例的分布
    failure_patterns = {}
    
    for feature in feature_columns:
        failure_values = failure_cases[feature]
        success_values = success_cases[feature]
        
        # 计算分位数
        failure_q25 = failure_values.quantile(0.25)
        failure_q50 = failure_values.quantile(0.50)
        failure_q75 = failure_values.quantile(0.75)
        
        success_q25 = success_values.quantile(0.25)
        success_q50 = success_values.quantile(0.50)
        success_q75 = success_values.quantile(0.75)
        
        failure_patterns[feature] = {
            'failure_q25': failure_q25,
            'failure_q50': failure_q50,
            'failure_q75': failure_q75,
            'success_q25': success_q25,
            'success_q50': success_q50,
            'success_q75': success_q75,
        }
    
    # 显示关键差异
    key_features = [stat['feature'] for stat in comparison_stats[:8]]
    
    print("📊 关键特征的分位数对比:")
    for feature in key_features:
        pattern = failure_patterns[feature]
        print(f"\n🔸 {feature}:")
        print(f"   失败案例: Q25={pattern['failure_q25']:.3f}, Q50={pattern['failure_q50']:.3f}, Q75={pattern['failure_q75']:.3f}")
        print(f"   成功案例: Q25={pattern['success_q25']:.3f}, Q50={pattern['success_q50']:.3f}, Q75={pattern['success_q75']:.3f}")
        
        # 判断失败案例的倾向
        if pattern['failure_q50'] > pattern['success_q50']:
            print(f"   ➡️ 失败案例倾向于更高的{feature}")
        else:
            print(f"   ➡️ 失败案例倾向于更低的{feature}")
    
    # 3. 训练专门识别失败案例的模型
    print("\n3️⃣ 训练失败案例识别模型:")
    print("-"*40)
    
    # 准备数据
    X = df[feature_columns].fillna(0)
    y = (~df['is_profitable']).astype(int)  # 反向标签：1=失败，0=成功
    
    print(f"📊 失败案例识别模型:")
    print(f"📊 特征维度: {X.shape}")
    print(f"📊 标签分布: 失败={y.sum()}, 成功={len(y)-y.sum()}")
    
    # 分割数据
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 训练模型
    models = {
        'RandomForest_Failure': RandomForestClassifier(n_estimators=100, random_state=42),
        'XGBoost_Failure': xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
    }
    
    failure_results = {}
    
    for name, model in models.items():
        print(f"\n🔧 训练 {name} 模型...")
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        accuracy = (y_pred == y_test).mean()
        
        print(f"📊 {name} 准确率: {accuracy:.3f}")
        
        # 特征重要性
        if hasattr(model, 'feature_importances_'):
            feature_importance = pd.DataFrame({
                'feature': feature_columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            print(f"🎯 {name} 重要特征 (导致失败):")
            for _, row in feature_importance.head(8).iterrows():
                print(f"   {row['feature']}: {row['importance']:.3f}")
        
        failure_results[name] = {
            'model': model,
            'accuracy': accuracy,
            'feature_importance': feature_importance if hasattr(model, 'feature_importances_') else None,
        }
    
    # 4. 失败案例的阈值分析
    print("\n4️⃣ 失败案例的阈值分析:")
    print("-"*40)
    
    # 分析每个特征在失败案例中的分布
    failure_thresholds = {}
    
    for feature in key_features:
        failure_values = failure_cases[feature]
        
        # 计算不同阈值下的失败率
        thresholds = np.percentile(failure_values, [10, 25, 50, 75, 90])
        
        print(f"\n🔸 {feature} 阈值分析:")
        for threshold in thresholds:
            # 低于阈值和高于阈值的失败率
            below_threshold = df[df[feature] <= threshold]['is_profitable'].mean()
            above_threshold = df[df[feature] > threshold]['is_profitable'].mean()
            
            print(f"   ≤{threshold:.3f}: 胜率={below_threshold*100:.1f}%")
            print(f"   >{threshold:.3f}: 胜率={above_threshold*100:.1f}%")
            
            # 找出最危险的阈值
            if below_threshold < above_threshold:
                print(f"   ⚠️ 低于{threshold:.3f}更容易失败")
            else:
                print(f"   ⚠️ 高于{threshold:.3f}更容易失败")
    
    # 5. 失败案例总结
    print("\n5️⃣ 失败案例总结:")
    print("-"*40)
    
    print("📋 导致收敛后下跌的主要因子:")
    
    # 基于统计分析和模型重要性，总结失败因子
    top_failure_features = []
    for stat in comparison_stats[:6]:
        feature = stat['feature']
        diff = stat['difference']
        
        if abs(diff) > 0.1:  # 显著差异
            if diff > 0:
                top_failure_features.append(f"{feature} 过高")
            else:
                top_failure_features.append(f"{feature} 过低")
    
    for i, factor in enumerate(top_failure_features):
        print(f"  {i+1}. {factor}")
    
    # 6. 反向策略建议
    print("\n6️⃣ 反向策略建议:")
    print("-"*40)
    
    print("🚫 避免以下特征的收敛区间:")
    
    # 基于分析结果给出具体的避免条件
    avoid_conditions = []
    
    for stat in comparison_stats[:5]:
        feature = stat['feature']
        diff = stat['difference']
        failure_mean = stat['failure_mean']
        
        if abs(diff) > 0.1:
            if diff > 0:
                # 成功案例该特征更高，失败案例更低
                # 所以要避免该特征过低的情况
                avoid_conditions.append(f"{feature} < {failure_mean:.3f}")
            else:
                # 成功案例该特征更低，失败案例更高
                # 所以要避免该特征过高的情况
                avoid_conditions.append(f"{feature} > {failure_mean:.3f}")
    
    for i, condition in enumerate(avoid_conditions):
        print(f"  {i+1}. 避免 {condition}")
    
    print(f"\n💡 反向策略核心思想:")
    print(f"   通过识别失败因子，我们可以:")
    print(f"   1. 避免具有失败特征的收敛区间")
    print(f"   2. 提高成功概率从37.5%到更高")
    print(f"   3. 减少不必要的投资风险")
    
    return {
        'comparison_stats': comparison_stats,
        'failure_patterns': failure_patterns,
        'failure_results': failure_results,
        'avoid_conditions': avoid_conditions
    }

if __name__ == "__main__":
    result = analyze_failure_factors()
    
    print(f"\n🎯 反向研究总结:")
    print("="*40)
    print("通过分析失败案例，我们发现了导致收敛后下跌的关键因子。")
    print("这些发现可以帮助我们避免高风险的投资机会，提高整体胜率。")
