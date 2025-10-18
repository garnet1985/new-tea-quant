#!/usr/bin/env python3
"""
V16综合优化分析：提升胜率 + 增加投资机会
目标：
1. 提升胜率从57.8%到60%+
2. 增加投资机会数量（当前4000+股票十几年不到2000个机会）
3. 保持或提升ROI到10%+
"""
import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Tuple
import warnings
warnings.filterwarnings('ignore')

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

def load_investment_data(tmp_dir: str) -> Tuple[List[Dict], Dict]:
    """加载投资数据"""
    print(f"📊 加载投资数据: {tmp_dir}")
    
    # 加载汇总数据
    summary_path = Path(tmp_dir) / "0_session_summary.json"
    with open(summary_path, 'r') as f:
        summary = json.load(f)
    
    print(f"总投资次数: {summary['total_investments']}")
    print(f"胜率: {summary['win_rate']:.2f}%")
    print(f"平均ROI: {summary['avg_roi']:.3f}")
    
    # 加载所有股票的投资记录
    investments = []
    stock_files = list(Path(tmp_dir).glob("*.json"))
    stock_files = [f for f in stock_files if f.name != "session_summary.json"]
    
    print(f"股票文件数量: {len(stock_files)}")
    
    for stock_file in stock_files:  # 分析所有文件
        try:
            with open(stock_file, 'r') as f:
                stock_data = json.load(f)
            
            stock_investments = stock_data.get('investments', [])
            for inv in stock_investments:
                # 检查是否有投资结果（已完成）
                if inv.get('result') in ['win', 'loss']:  # 只分析已完成的投资
                    # 转换result为is_successful格式
                    inv['is_successful'] = (inv['result'] == 'win')
                    # 转换ROI格式
                    if 'overall_profit_rate' in inv:
                        inv['roi'] = inv['overall_profit_rate']
                    investments.append(inv)
        except Exception as e:
            print(f"加载文件失败 {stock_file}: {e}")
    
    print(f"有效投资记录: {len(investments)}")
    return investments, summary

def extract_features(investments: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
    """提取特征和标签"""
    print("🔍 提取特征...")
    
    features_list = []
    labels = []
    
    for inv in investments:
        try:
            # 提取信号条件特征
            signal_conditions = inv.get('extra_fields', {}).get('signal_conditions', {})
            
            if not signal_conditions:
                continue
            
            # 核心特征
            features = {
                'ma_convergence': signal_conditions.get('ma_convergence', 0),
                'ma20_slope': signal_conditions.get('ma20_slope', 0),
                'ma60_slope': signal_conditions.get('ma60_slope', 0),
                'volume_trend': signal_conditions.get('volume_trend', 0),
                'amount_ratio': signal_conditions.get('amount_ratio', 1),
                'historical_percentile': signal_conditions.get('historical_percentile', 0.5),
                'oscillation_position': signal_conditions.get('oscillation_position', 0.5),
                'volume_confirmation': signal_conditions.get('volume_confirmation', 1),
                'rsi_signal': signal_conditions.get('rsi_signal', 50),
            }
            
            # 投资结果特征
            features['duration_days'] = inv.get('duration_days', 0)
            features['max_gain'] = inv.get('max_gain', 0)
            features['max_loss'] = inv.get('max_loss', 0)
            features['roi'] = inv.get('roi', 0)
            
            features_list.append(list(features.values()))
            labels.append(1 if inv.get('is_successful') else 0)
            
        except Exception as e:
            print(f"提取特征失败: {e}")
            continue
    
    X = np.array(features_list)
    y = np.array(labels)
    
    print(f"特征维度: {X.shape}")
    print(f"标签分布: 成功={np.sum(y)}, 失败={np.sum(1-y)}")
    
    return X, y

def analyze_feature_importance(X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    """分析特征重要性"""
    print("🎯 分析特征重要性...")
    
    feature_names = [
        'ma_convergence', 'ma20_slope', 'ma60_slope', 'volume_trend', 'amount_ratio',
        'historical_percentile', 'oscillation_position', 'volume_confirmation', 'rsi_signal',
        'duration_days', 'max_gain', 'max_loss', 'roi'
    ]
    
    # 训练随机森林
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    # 获取特征重要性
    importance = rf.feature_importances_
    feature_importance = dict(zip(feature_names, importance))
    
    # 排序
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    
    print("\n📊 特征重要性排序:")
    for feature, imp in sorted_features:
        print(f"  {feature}: {imp:.4f}")
    
    return feature_importance

def analyze_condition_thresholds(investments: List[Dict]) -> Dict[str, Dict]:
    """分析当前条件阈值的效果"""
    print("📈 分析条件阈值...")
    
    # 统计各种条件下的成功率
    conditions_analysis = {}
    
    # 分析MA收敛度
    ma_convergence_ranges = [
        (0, 0.05, "很收敛"),
        (0.05, 0.08, "较收敛"), 
        (0.08, 0.12, "中等收敛"),
        (0.12, 0.2, "较发散"),
        (0.2, 1.0, "很发散")
    ]
    
    print("\n🔍 MA收敛度分析:")
    for min_val, max_val, label in ma_convergence_ranges:
        filtered_inv = [
            inv for inv in investments 
            if inv.get('extra_fields', {}).get('signal_conditions', {}).get('ma_convergence', 0) >= min_val
            and inv.get('extra_fields', {}).get('signal_conditions', {}).get('ma_convergence', 0) < max_val
            and inv.get('result') in ['win', 'loss']
        ]
        
        if filtered_inv:
            success_rate = np.mean([inv['is_successful'] for inv in filtered_inv])
            avg_roi = np.mean([inv.get('roi', 0) for inv in filtered_inv])
            count = len(filtered_inv)
            print(f"  {label} ({min_val}-{max_val}): 成功率={success_rate:.2%}, 平均ROI={avg_roi:.2%}, 数量={count}")
    
    # 分析历史分位数
    print("\n🔍 历史分位数分析:")
    percentile_ranges = [
        (0, 0.2, "很低"),
        (0.2, 0.35, "较低"),
        (0.35, 0.5, "中等"),
        (0.5, 0.7, "较高"),
        (0.7, 1.0, "很高")
    ]
    
    for min_val, max_val, label in percentile_ranges:
        filtered_inv = [
            inv for inv in investments 
            if inv.get('extra_fields', {}).get('signal_conditions', {}).get('historical_percentile', 0.5) >= min_val
            and inv.get('extra_fields', {}).get('signal_conditions', {}).get('historical_percentile', 0.5) < max_val
            and inv.get('result') in ['win', 'loss']
        ]
        
        if filtered_inv:
            success_rate = np.mean([inv['is_successful'] for inv in filtered_inv])
            avg_roi = np.mean([inv.get('roi', 0) for inv in filtered_inv])
            count = len(filtered_inv)
            print(f"  {label} ({min_val}-{max_val}): 成功率={success_rate:.2%}, 平均ROI={avg_roi:.2%}, 数量={count}")

def suggest_optimizations(investments: List[Dict], feature_importance: Dict[str, float]) -> Dict[str, Any]:
    """基于分析结果提出优化建议"""
    print("\n💡 优化建议:")
    
    suggestions = {
        'loosen_conditions': [],
        'tighten_conditions': [],
        'new_conditions': [],
        'expected_impact': {}
    }
    
    # 分析当前条件过于严格的地方
    total_completed = len([inv for inv in investments if inv.get('result') in ['win', 'loss']])
    
    # 1. MA收敛度分析 - 看是否可以放宽
    current_ma_threshold = 0.09
    ma_convergence_data = [
        inv.get('extra_fields', {}).get('signal_conditions', {}).get('ma_convergence', 0)
        for inv in investments if inv.get('result') in ['win', 'loss']
    ]
    
    if ma_convergence_data:
        current_success_rate = np.mean([inv['is_successful'] for inv in investments if inv.get('result') in ['win', 'loss']])
        
        # 尝试放宽MA收敛度到0.12
        looser_ma_inv = [
            inv for inv in investments 
            if inv.get('extra_fields', {}).get('signal_conditions', {}).get('ma_convergence', 0) < 0.12
            and inv.get('result') in ['win', 'loss']
        ]
        
        if looser_ma_inv:
            looser_success_rate = np.mean([inv['is_successful'] for inv in looser_ma_inv])
            looser_roi = np.mean([inv.get('roi', 0) for inv in looser_ma_inv])
            additional_opportunities = len(looser_ma_inv) - total_completed
            
            print(f"📊 MA收敛度放宽分析:")
            print(f"  当前阈值0.09: 成功率={current_success_rate:.2%}")
            print(f"  放宽到0.12: 成功率={looser_success_rate:.2%}, ROI={looser_roi:.2%}, 额外机会={additional_opportunities}")
            
            if looser_success_rate >= 0.58:  # 如果能保持58%以上成功率
                suggestions['loosen_conditions'].append({
                    'condition': 'ma_convergence',
                    'current': 0.09,
                    'suggested': 0.12,
                    'expected_success_rate': looser_success_rate,
                    'expected_roi': looser_roi,
                    'additional_opportunities': additional_opportunities
                })
    
    # 2. 历史分位数分析
    current_percentile_threshold = 0.35
    percentile_data = [
        inv.get('extra_fields', {}).get('signal_conditions', {}).get('historical_percentile', 0.5)
        for inv in investments if inv.get('result') in ['win', 'loss']
    ]
    
    if percentile_data:
        # 尝试放宽到0.4
        looser_percentile_inv = [
            inv for inv in investments 
            if inv.get('extra_fields', {}).get('signal_conditions', {}).get('historical_percentile', 0.5) < 0.4
            and inv.get('result') in ['win', 'loss']
        ]
        
        if looser_percentile_inv:
            looser_success_rate = np.mean([inv['is_successful'] for inv in looser_percentile_inv])
            looser_roi = np.mean([inv.get('roi', 0) for inv in looser_percentile_inv])
            additional_opportunities = len(looser_percentile_inv) - total_completed
            
            print(f"📊 历史分位数放宽分析:")
            print(f"  当前阈值0.35: 成功率={current_success_rate:.2%}")
            print(f"  放宽到0.4: 成功率={looser_success_rate:.2%}, ROI={looser_roi:.2%}, 额外机会={additional_opportunities}")
            
            if looser_success_rate >= 0.58:
                suggestions['loosen_conditions'].append({
                    'condition': 'historical_percentile',
                    'current': 0.35,
                    'suggested': 0.4,
                    'expected_success_rate': looser_success_rate,
                    'expected_roi': looser_roi,
                    'additional_opportunities': additional_opportunities
                })
    
    return suggestions

def main():
    print("🚀 V16综合优化分析开始...")
    
    # 加载数据
    tmp_dir = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp/2025_10_17-202"
    investments, summary = load_investment_data(tmp_dir)
    
    if len(investments) < 100:
        print("❌ 投资记录太少，无法进行有效分析")
        return
    
    # 提取特征
    X, y = extract_features(investments)
    
    # 分析特征重要性
    feature_importance = analyze_feature_importance(X, y)
    
    # 分析条件阈值
    analyze_condition_thresholds(investments)
    
    # 提出优化建议
    suggestions = suggest_optimizations(investments, feature_importance)
    
    print("\n🎯 总结:")
    print(f"当前胜率: {summary['win_rate']:.1f}%")
    print(f"当前ROI: {summary['avg_roi']:.3f}")
    print(f"投资机会: {summary['total_investments']}次")
    
    if suggestions['loosen_conditions']:
        print("\n💡 建议放宽的条件:")
        for suggestion in suggestions['loosen_conditions']:
            print(f"  {suggestion['condition']}: {suggestion['current']} → {suggestion['suggested']}")
            print(f"    预期胜率: {suggestion['expected_success_rate']:.1%}")
            print(f"    预期ROI: {suggestion['expected_roi']:.2%}")
            print(f"    额外机会: +{suggestion['additional_opportunities']}次")

if __name__ == "__main__":
    main()
