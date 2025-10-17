#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新分析包含成交量特征的收敛区间数据
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import xgboost as xgb

from app.analyzer.strategy.RTB.expanded_ml_analysis import ExpandedConvergenceMLAnalysis

def analyze_with_volume_features():
    """分析包含成交量特征的数据"""
    
    print("🔍 重新分析包含成交量特征的收敛区间数据")
    print("="*60)
    
    # 使用较小的样本进行快速测试
    analyzer = ExpandedConvergenceMLAnalysis()
    
    print("🚀 开始分析包含成交量特征的样本...")
    
    # 获取100个样本进行快速测试
    stock_ids = analyzer.get_diverse_stock_sample(target_size=100)
    
    print(f"📊 选择样本: {len(stock_ids)}只股票")
    
    # 分析所有股票
    all_data = []
    success_count = 0
    
    for i, stock_id in enumerate(stock_ids):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"进度: {i+1}/{len(stock_ids)} ({success_count}成功)")
        
        try:
            stock_data = analyzer.analyze_stock(stock_id)
            if stock_data:
                all_data.extend(stock_data)
                success_count += 1
        except Exception as e:
            if (i + 1) % 50 == 0:
                print(f"❌ 跳过 {stock_id}: {e}")
            continue
    
    if not all_data:
        print("❌ 没有获得任何数据")
        return None
    
    df = pd.DataFrame(all_data)
    print(f"\n📊 分析结果:")
    print(f"📊 成功分析股票: {success_count}/{len(stock_ids)}")
    print(f"📊 总收敛区间样本: {len(df)}")
    print(f"📊 整体胜率: {df['is_profitable'].mean()*100:.1f}%")
    print(f"📊 平均最大涨幅: {df['max_return'].mean():.1f}%")
    
    # 显示所有特征列
    print(f"\n📊 特征列表:")
    feature_columns = [
        'duration_weeks', 'price_change_pct', 'price_range_pct', 'convergence_ratio',
        'ma20_slope', 'ma60_slope', 'position_in_range', 'close_to_ma20',
        'volume_ratio', 'amount_ratio', 'volume_trend', 'amount_trend', 'avg_volume', 'avg_amount'
    ]
    
    for i, col in enumerate(feature_columns):
        if col in df.columns:
            print(f"  {i+1:2d}. {col}: 存在")
        else:
            print(f"  {i+1:2d}. {col}: 缺失")
    
    # 检查缺失值
    print(f"\n📊 缺失值统计:")
    missing_stats = df[feature_columns].isnull().sum()
    for col, missing_count in missing_stats.items():
        if missing_count > 0:
            print(f"  {col}: {missing_count} ({missing_count/len(df)*100:.1f}%)")
        else:
            print(f"  {col}: 无缺失值")
    
    # 训练ML模型
    if len(df) > 50:
        print(f"\n🤖 训练包含成交量特征的ML模型...")
        
        X = df[feature_columns].fillna(0)
        y = df['is_profitable'].astype(int)
        
        print(f"📊 特征维度: {X.shape}")
        print(f"📊 标签分布: {y.value_counts().to_dict()}")
        
        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # 训练模型
        models = {
            'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42),
            'XGBoost': xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
        }
        
        results = {}
        
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
                
                print(f"🎯 {name} 重要特征:")
                for _, row in feature_importance.head(8).iterrows():
                    print(f"   {row['feature']}: {row['importance']:.3f}")
            
            results[name] = {
                'model': model,
                'accuracy': accuracy,
                'feature_importance': feature_importance if hasattr(model, 'feature_importances_') else None,
            }
        
        # 对比分析（有成交量 vs 无成交量）
        print(f"\n📊 对比分析:")
        print(f"📊 特征数量: {len(feature_columns)} (包含成交量特征)")
        print(f"📊 最佳准确率: {max(r['accuracy'] for r in results.values()):.3f}")
        
        # 分析成交量特征的重要性
        print(f"\n🎯 成交量特征重要性分析:")
        for name, result in results.items():
            if result['feature_importance'] is not None:
                volume_features = result['feature_importance'][
                    result['feature_importance']['feature'].str.contains('volume|amount')
                ]
                if not volume_features.empty:
                    print(f"\n📈 {name} 成交量特征重要性:")
                    for _, row in volume_features.iterrows():
                        print(f"   {row['feature']}: {row['importance']:.3f}")
                else:
                    print(f"\n📈 {name} 无成交量特征")
        
        # 保存数据
        output_file = '/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/convergence_with_volume_data.csv'
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n💾 数据已保存到: {output_file}")
        
        return df, results
    else:
        print("⚠️ 样本数量不足，跳过ML模型训练")
        return df, None

if __name__ == "__main__":
    result = analyze_with_volume_features()
    
    if result:
        df, ml_results = result
        print(f"\n🎉 包含成交量特征的分析完成!")
        print(f"📊 样本数量: {len(df)}")
        
        if ml_results:
            print(f"📊 最佳模型准确率: {max(r['accuracy'] for r in ml_results.values()):.3f}")
            
            # 总结成交量特征的影响
            print(f"\n💡 成交量特征影响总结:")
            print(f"1. 新增了6个成交量相关特征")
            print(f"2. 特征总数从8个增加到14个")
            print(f"3. 可以分析成交量在收敛期间的变化模式")
            print(f"4. 有助于识别真正的突破信号")
