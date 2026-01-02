#!/usr/bin/env python3
"""
优化RTB条件以让更多脚本识别的反转点通过
分析脚本识别的反转点特征，找出RTB需要调整的条件
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.append('/Users/garnet/Desktop/stocks-py')

from app.analyzer.strategy.RTB.feature_identity.reversal_data_generator_enhanced import EnhancedReversalDataGenerator
from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings
from app.core_modules.data_manager.data_manager import DataManager
from utils.db.db_manager import DatabaseManager

def load_script_reversals():
    """加载脚本找到的反转点"""
    try:
        generator = EnhancedReversalDataGenerator()
        stock_list = generator.get_sample_list()
        
        script_reversals = []
        
        # 处理前20只股票作为样本
        for i, stock in enumerate(stock_list[:20]):
            stock_code = stock['id'] if isinstance(stock, dict) else stock
            print(f"🔄 处理股票 {i+1}/20: {stock_code}")
            
            try:
                reversals = generator.identify_reversal_for_stock(stock_code)
                
                for reversal in reversals:
                    script_reversals.append({
                        'stock_code': stock_code,
                        'stock_name': reversal.get('stock_name', ''),
                        'entry_date': reversal.get('date'),
                        'entry_price': reversal.get('price'),
                        'roi': reversal.get('gain', 0),
                        'source': 'Script'
                    })
                    
            except Exception as e:
                print(f"❌ 处理股票 {stock_code} 时出错: {e}")
                continue
        
        print(f"✅ 加载了 {len(script_reversals)} 个脚本反转点")
        return script_reversals
        
    except Exception as e:
        print(f"❌ 加载脚本反转点时出错: {e}")
        return []

def analyze_script_reversal_features(script_reversals):
    """分析脚本反转点的特征分布"""
    if not script_reversals:
        print("❌ 没有脚本反转点可分析")
        return None
    
    print("\n" + "="*60)
    print("🔍 脚本反转点特征分析")
    print("="*60)
    
    # 初始化RTB策略和数据加载器
    db_manager = DatabaseManager()
    rtb_strategy = ReverseTrendBet(db_manager)
    data_mgr = DataManager(is_verbose=False)
    
    feature_stats = {
        'market_cap': [],
        'pe_ratio': [],
        'pb_ratio': [],
        'rsi': [],
        'price_percentile': [],
        'volatility': [],
        'volume_ratio_before': [],
        'volume_ratio_after': [],
        'ma_convergence': [],
        'price_vs_ma20': [],
        'price_vs_ma60': [],
        'monthly_drop_rate': [],
        'ma20_slope': [],
    }
    
    failed_count = 0
    success_count = 0
    
    for i, reversal in enumerate(script_reversals):
        stock_code = reversal['stock_code']
        entry_date = reversal['entry_date']
        
        if i % 10 == 0:
            print(f"🔄 分析特征 {i+1}/{len(script_reversals)}: {stock_code} {entry_date}")
        
        try:
            # 获取周线数据
            weekly_klines = data_mgr.load_klines(
                stock_id=stock_code,
                term='weekly'
            )
            
            if weekly_klines.empty:
                failed_count += 1
                continue
            
            # 计算特征
            features = rtb_strategy._calculate_ml_enhanced_features(weekly_klines, stock_code, db_manager)
            
            if features is None:
                failed_count += 1
                continue
            
            # 收集特征数据
            for feature_name in feature_stats.keys():
                if feature_name in features:
                    feature_stats[feature_name].append(features[feature_name])
            
            success_count += 1
            
        except Exception as e:
            failed_count += 1
            continue
    
    print(f"\n📊 特征计算完成: 成功 {success_count}, 失败 {failed_count}")
    
    # 计算特征统计
    feature_analysis = {}
    for feature_name, values in feature_stats.items():
        if values:
            feature_analysis[feature_name] = {
                'count': len(values),
                'mean': np.mean(values),
                'median': np.median(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'q25': np.percentile(values, 25),
                'q75': np.percentile(values, 75),
            }
    
    return feature_analysis

def analyze_current_rtb_conditions():
    """分析当前RTB条件"""
    print("\n" + "="*60)
    print("🔍 当前RTB条件分析")
    print("="*60)
    
    current_conditions = {
        'market_cap': {'max': 1200000, 'min': None},
        'pe_ratio': {'max': 80, 'min': 3},
        'pb_ratio': {'max': 5.0, 'min': 0.1},
        'rsi': {'max': 85, 'min': 15},
        'price_percentile': {'max': 0.80, 'min': 0.05},
        'volatility': {'max': 0.30, 'min': 0.01},
        'volume_ratio_before': {'min': 1.0, 'max': None},
        'volume_ratio_after': {'min': 1.0, 'max': None},
        'ma_convergence': {'max': 0.15, 'min': None},
        'price_vs_ma20': {'max': 0.15, 'min': -0.15},
        'price_vs_ma60': {'max': 0.20, 'min': -0.20},
        'monthly_drop_rate': {'max': 0.70, 'min': 0.01},
        'ma20_slope': {'min': -0.05, 'max': None},
    }
    
    return current_conditions

def recommend_condition_adjustments(script_features, current_conditions):
    """推荐条件调整"""
    print("\n" + "="*60)
    print("💡 RTB条件调整建议")
    print("="*60)
    
    adjustments = {}
    
    for feature_name, script_stats in script_features.items():
        if feature_name not in current_conditions:
            continue
        
        current_cond = current_conditions[feature_name]
        script_min = script_stats['min']
        script_max = script_stats['max']
        script_mean = script_stats['mean']
        script_q25 = script_stats['q25']
        script_q75 = script_stats['q75']
        
        print(f"\n📊 {feature_name}:")
        print(f"  脚本反转点范围: {script_min:.4f} ~ {script_max:.4f}")
        print(f"  脚本反转点均值: {script_mean:.4f}")
        print(f"  脚本反转点Q25-Q75: {script_q25:.4f} ~ {script_q75:.4f}")
        
        # 分析当前条件是否过于严格
        if current_cond.get('max') is not None:
            if script_max > current_cond['max']:
                # 脚本最大值超过当前上限，需要放宽
                new_max = min(script_max * 1.1, script_q75 * 2)  # 给一些缓冲
                adjustments[feature_name] = {'max': new_max}
                print(f"  🔴 当前上限 {current_cond['max']:.4f} 过于严格")
                print(f"  💡 建议调整上限到: {new_max:.4f}")
        
        if current_cond.get('min') is not None:
            if script_min < current_cond['min']:
                # 脚本最小值低于当前下限，需要放宽
                new_min = max(script_min * 0.9, script_q25 * 0.5)  # 给一些缓冲
                adjustments[feature_name] = {'min': new_min}
                print(f"  🔴 当前下限 {current_cond['min']:.4f} 过于严格")
                print(f"  💡 建议调整下限到: {new_min:.4f}")
        
        # 检查是否有条件过于宽松
        if current_cond.get('max') is not None and current_cond.get('min') is not None:
            if script_max < current_cond['min'] or script_min > current_cond['max']:
                print(f"  🟡 当前条件 {current_cond['min']:.4f} ~ {current_cond['max']:.4f} 可能过于宽松")
    
    return adjustments

def generate_optimized_conditions(adjustments):
    """生成优化后的条件代码"""
    print("\n" + "="*60)
    print("🔧 优化后的RTB条件代码")
    print("="*60)
    
    optimized_conditions = {
        'market_cap': {'max': 1200000, 'min': None},
        'pe_ratio': {'max': 80, 'min': 3},
        'pb_ratio': {'max': 5.0, 'min': 0.1},
        'rsi': {'max': 85, 'min': 15},
        'price_percentile': {'max': 0.80, 'min': 0.05},
        'volatility': {'max': 0.30, 'min': 0.01},
        'volume_ratio_before': {'min': 1.0, 'max': None},
        'volume_ratio_after': {'min': 1.0, 'max': None},
        'ma_convergence': {'max': 0.15, 'min': None},
        'price_vs_ma20': {'max': 0.15, 'min': -0.15},
        'price_vs_ma60': {'max': 0.20, 'min': -0.20},
        'monthly_drop_rate': {'max': 0.70, 'min': 0.01},
        'ma20_slope': {'min': -0.05, 'max': None},
    }
    
    # 应用调整
    for feature_name, adjustment in adjustments.items():
        if feature_name in optimized_conditions:
            optimized_conditions[feature_name].update(adjustment)
    
    # 生成代码
    print("```python")
    print("conditions = [")
    
    for feature_name, condition in optimized_conditions.items():
        if condition.get('max') is not None and condition.get('min') is not None:
            print(f"    # {feature_name}")
            print(f"    features['{feature_name}'] < {condition['max']:.4f},  # 上限")
            print(f"    features['{feature_name}'] > {condition['min']:.4f},  # 下限")
        elif condition.get('max') is not None:
            print(f"    # {feature_name}")
            print(f"    features['{feature_name}'] < {condition['max']:.4f},  # 上限")
        elif condition.get('min') is not None:
            print(f"    # {feature_name}")
            print(f"    features['{feature_name}'] > {condition['min']:.4f},  # 下限")
    
    print("]")
    print("```")
    
    return optimized_conditions

def main():
    """主函数"""
    print("🚀 开始优化RTB条件以让更多脚本反转点通过")
    
    # 加载脚本反转点
    script_reversals = load_script_reversals()
    if not script_reversals:
        print("❌ 无法加载脚本反转点")
        return
    
    # 分析脚本反转点特征
    script_features = analyze_script_reversal_features(script_reversals)
    if not script_features:
        print("❌ 无法分析脚本反转点特征")
        return
    
    # 分析当前RTB条件
    current_conditions = analyze_current_rtb_conditions()
    
    # 推荐调整
    adjustments = recommend_condition_adjustments(script_features, current_conditions)
    
    # 生成优化后的条件
    optimized_conditions = generate_optimized_conditions(adjustments)
    
    print("\n✅ 优化分析完成！")
    print("💡 建议根据上述调整修改RTB策略的筛选条件")

if __name__ == "__main__":
    main()
