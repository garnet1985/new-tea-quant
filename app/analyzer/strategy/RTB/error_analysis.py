#!/usr/bin/env python3
"""
深入分析收敛时间段的错误案例，找出失败原因和避免区域
"""
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader

# 尝试导入机器学习库
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
    from sklearn.preprocessing import StandardScaler
    import xgboost as xgb
    ML_AVAILABLE = True
except ImportError:
    print("⚠️  机器学习库未安装，将使用基础统计分析")
    ML_AVAILABLE = False

def load_convergence_data():
    """加载之前分析的收敛时间段数据"""
    data_file = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/convergence_periods_analysis.csv"
    
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return None
    
    df = pd.read_csv(data_file)
    print(f"📊 加载数据: {len(df)} 个收敛时间段")
    return df

def analyze_error_patterns(df):
    """分析错误模式"""
    print("\n" + "="*80)
    print("🔍 错误案例分析")
    print("="*80)
    
    # 过滤掉包含NaN的数据
    df_clean = df.dropna()
    
    # 定义成功和失败案例
    success_cases = df_clean[df_clean['is_profitable_20w'] == 1]
    failure_cases = df_clean[df_clean['is_profitable_20w'] == 0]
    
    print(f"📈 成功案例: {len(success_cases)} 个")
    print(f"❌ 失败案例: {len(failure_cases)} 个")
    print(f"🎯 胜率: {len(success_cases) / len(df_clean) * 100:.1f}%")
    
    # 分析失败案例的特征分布
    print(f"\n📊 失败案例特征分析:")
    print("-" * 60)
    
    features = ['avg_convergence', 'ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end', 'duration_weeks']
    feature_names = ['平均收敛度', 'MA20斜率(开始)', 'MA60斜率(开始)', 'MA20斜率(结束)', 'MA60斜率(结束)', '持续时间']
    
    for feature, name in zip(features, feature_names):
        if feature in df_clean.columns:
            success_mean = success_cases[feature].mean()
            failure_mean = failure_cases[feature].mean()
            success_std = success_cases[feature].std()
            failure_std = failure_cases[feature].std()
            
            print(f"\n{name}:")
            print(f"   成功案例: 均值={success_mean:.4f}, 标准差={success_std:.4f}")
            print(f"   失败案例: 均值={failure_mean:.4f}, 标准差={failure_std:.4f}")
            print(f"   差异: {success_mean - failure_mean:.4f}")
            
            # 分析失败案例的分布区间
            if feature == 'avg_convergence':
                print(f"   失败案例收敛度分布:")
                for threshold in [0.03, 0.05, 0.07, 0.08, 0.10]:
                    subset = failure_cases[failure_cases[feature] < threshold]
                    if len(subset) > 0:
                        ratio = len(subset) / len(failure_cases) * 100
                        avg_return = subset['return_20w'].mean() * 100
                        print(f"     <{threshold}: {len(subset)}个({ratio:.1f}%), 平均收益{avg_return:.1f}%")
            
            elif feature in ['ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end']:
                print(f"   失败案例斜率分布:")
                for slope_range in [(-0.2, -0.1), (-0.1, -0.05), (-0.05, 0), (0, 0.05), (0.05, 0.1), (0.1, 0.2)]:
                    subset = failure_cases[(failure_cases[feature] >= slope_range[0]) & (failure_cases[feature] < slope_range[1])]
                    if len(subset) > 0:
                        ratio = len(subset) / len(failure_cases) * 100
                        avg_return = subset['return_20w'].mean() * 100
                        print(f"     {slope_range[0]}~{slope_range[1]}: {len(subset)}个({ratio:.1f}%), 平均收益{avg_return:.1f}%")
            
            elif feature == 'duration_weeks':
                print(f"   失败案例持续时间分布:")
                for duration_range in [(1, 5), (5, 10), (10, 20), (20, 50)]:
                    subset = failure_cases[(failure_cases[feature] >= duration_range[0]) & (failure_cases[feature] < duration_range[1])]
                    if len(subset) > 0:
                        ratio = len(subset) / len(failure_cases) * 100
                        avg_return = subset['return_20w'].mean() * 100
                        print(f"     {duration_range[0]}~{duration_range[1]}周: {len(subset)}个({ratio:.1f}%), 平均收益{avg_return:.1f}%")

def find_high_risk_zones(df):
    """找出高风险区域"""
    print(f"\n" + "="*80)
    print("⚠️  高风险区域识别")
    print("="*80)
    
    df_clean = df.dropna()
    
    # 定义高风险区域：胜率低于40%的参数组合
    high_risk_zones = []
    
    features = ['avg_convergence', 'ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end', 'duration_weeks']
    feature_names = ['平均收敛度', 'MA20斜率(开始)', 'MA60斜率(开始)', 'MA20斜率(结束)', 'MA60斜率(结束)', '持续时间']
    
    for feature, name in zip(features, feature_names):
        if feature == 'avg_convergence':
            # 分析不同收敛度区间的胜率
            for threshold in [0.03, 0.05, 0.07, 0.08, 0.10]:
                subset = df_clean[df_clean[feature] < threshold]
                if len(subset) >= 10:  # 至少10个样本
                    win_rate = subset['is_profitable_20w'].mean() * 100
                    avg_return = subset['return_20w'].mean() * 100
                    if win_rate < 40:
                        high_risk_zones.append({
                            'feature': name,
                            'condition': f"< {threshold}",
                            'samples': len(subset),
                            'win_rate': win_rate,
                            'avg_return': avg_return,
                            'risk_level': 'HIGH' if win_rate < 30 else 'MEDIUM'
                        })
        
        elif feature in ['ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end']:
            # 分析不同斜率区间的胜率
            for slope_range in [(-0.2, -0.1), (-0.1, -0.05), (-0.05, 0), (0, 0.05), (0.05, 0.1), (0.1, 0.2)]:
                subset = df_clean[(df_clean[feature] >= slope_range[0]) & (df_clean[feature] < slope_range[1])]
                if len(subset) >= 10:
                    win_rate = subset['is_profitable_20w'].mean() * 100
                    avg_return = subset['return_20w'].mean() * 100
                    if win_rate < 40:
                        high_risk_zones.append({
                            'feature': name,
                            'condition': f"{slope_range[0]} ~ {slope_range[1]}",
                            'samples': len(subset),
                            'win_rate': win_rate,
                            'avg_return': avg_return,
                            'risk_level': 'HIGH' if win_rate < 30 else 'MEDIUM'
                        })
        
        elif feature == 'duration_weeks':
            # 分析不同持续时间区间的胜率
            for duration_range in [(1, 5), (5, 10), (10, 20), (20, 50)]:
                subset = df_clean[(df_clean[feature] >= duration_range[0]) & (df_clean[feature] < duration_range[1])]
                if len(subset) >= 10:
                    win_rate = subset['is_profitable_20w'].mean() * 100
                    avg_return = subset['return_20w'].mean() * 100
                    if win_rate < 40:
                        high_risk_zones.append({
                            'feature': name,
                            'condition': f"{duration_range[0]} ~ {duration_range[1]}周",
                            'samples': len(subset),
                            'win_rate': win_rate,
                            'avg_return': avg_return,
                            'risk_level': 'HIGH' if win_rate < 30 else 'MEDIUM'
                        })
    
    # 按风险等级和胜率排序
    high_risk_zones.sort(key=lambda x: (x['risk_level'], x['win_rate']))
    
    print(f"🚨 发现 {len(high_risk_zones)} 个高风险区域:")
    print("-" * 80)
    
    for i, zone in enumerate(high_risk_zones, 1):
        print(f"{i:2d}. {zone['feature']}: {zone['condition']}")
        print(f"    样本数: {zone['samples']}, 胜率: {zone['win_rate']:.1f}%, 平均收益: {zone['avg_return']:.1f}%")
        print(f"    风险等级: {zone['risk_level']}")
        print()
    
    return high_risk_zones

def find_optimal_zones(df):
    """找出最优区域"""
    print(f"\n" + "="*80)
    print("✅ 最优区域识别")
    print("="*80)
    
    df_clean = df.dropna()
    
    # 定义最优区域：胜率高于60%的参数组合
    optimal_zones = []
    
    features = ['avg_convergence', 'ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end', 'duration_weeks']
    feature_names = ['平均收敛度', 'MA20斜率(开始)', 'MA60斜率(开始)', 'MA20斜率(结束)', 'MA60斜率(结束)', '持续时间']
    
    for feature, name in zip(features, feature_names):
        if feature == 'avg_convergence':
            # 分析不同收敛度区间的胜率
            for threshold in [0.03, 0.05, 0.07, 0.08, 0.10]:
                subset = df_clean[df_clean[feature] < threshold]
                if len(subset) >= 10:  # 至少10个样本
                    win_rate = subset['is_profitable_20w'].mean() * 100
                    avg_return = subset['return_20w'].mean() * 100
                    if win_rate > 60:
                        optimal_zones.append({
                            'feature': name,
                            'condition': f"< {threshold}",
                            'samples': len(subset),
                            'win_rate': win_rate,
                            'avg_return': avg_return,
                            'quality': 'EXCELLENT' if win_rate > 70 else 'GOOD'
                        })
        
        elif feature in ['ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end']:
            # 分析不同斜率区间的胜率
            for slope_range in [(-0.2, -0.1), (-0.1, -0.05), (-0.05, 0), (0, 0.05), (0.05, 0.1), (0.1, 0.2)]:
                subset = df_clean[(df_clean[feature] >= slope_range[0]) & (df_clean[feature] < slope_range[1])]
                if len(subset) >= 10:
                    win_rate = subset['is_profitable_20w'].mean() * 100
                    avg_return = subset['return_20w'].mean() * 100
                    if win_rate > 60:
                        optimal_zones.append({
                            'feature': name,
                            'condition': f"{slope_range[0]} ~ {slope_range[1]}",
                            'samples': len(subset),
                            'win_rate': win_rate,
                            'avg_return': avg_return,
                            'quality': 'EXCELLENT' if win_rate > 70 else 'GOOD'
                        })
        
        elif feature == 'duration_weeks':
            # 分析不同持续时间区间的胜率
            for duration_range in [(1, 5), (5, 10), (10, 20), (20, 50)]:
                subset = df_clean[(df_clean[feature] >= duration_range[0]) & (df_clean[feature] < duration_range[1])]
                if len(subset) >= 10:
                    win_rate = subset['is_profitable_20w'].mean() * 100
                    avg_return = subset['return_20w'].mean() * 100
                    if win_rate > 60:
                        optimal_zones.append({
                            'feature': name,
                            'condition': f"{duration_range[0]} ~ {duration_range[1]}周",
                            'samples': len(subset),
                            'win_rate': win_rate,
                            'avg_return': avg_return,
                            'quality': 'EXCELLENT' if win_rate > 70 else 'GOOD'
                        })
    
    # 按质量等级和胜率排序
    optimal_zones.sort(key=lambda x: (x['quality'], -x['win_rate']))
    
    print(f"🎯 发现 {len(optimal_zones)} 个最优区域:")
    print("-" * 80)
    
    for i, zone in enumerate(optimal_zones, 1):
        print(f"{i:2d}. {zone['feature']}: {zone['condition']}")
        print(f"    样本数: {zone['samples']}, 胜率: {zone['win_rate']:.1f}%, 平均收益: {zone['avg_return']:.1f}%")
        print(f"    质量等级: {zone['quality']}")
        print()
    
    return optimal_zones

def analyze_combined_conditions(df):
    """分析组合条件的效果"""
    print(f"\n" + "="*80)
    print("🔗 组合条件分析")
    print("="*80)
    
    df_clean = df.dropna()
    
    # 分析一些关键组合条件
    combinations = [
        {
            'name': 'MA20结束斜率 > 0.1',
            'condition': df_clean['ma20_slope_end'] > 0.1
        },
        {
            'name': 'MA20开始斜率 > 0.05',
            'condition': df_clean['ma20_slope_start'] > 0.05
        },
        {
            'name': '收敛度 < 0.07',
            'condition': df_clean['avg_convergence'] < 0.07
        },
        {
            'name': '持续时间 5-10周',
            'condition': (df_clean['duration_weeks'] >= 5) & (df_clean['duration_weeks'] < 10)
        },
        {
            'name': 'MA20结束斜率 > 0.1 AND 收敛度 < 0.07',
            'condition': (df_clean['ma20_slope_end'] > 0.1) & (df_clean['avg_convergence'] < 0.07)
        },
        {
            'name': 'MA20开始斜率 > 0.05 AND MA20结束斜率 > 0.1',
            'condition': (df_clean['ma20_slope_start'] > 0.05) & (df_clean['ma20_slope_end'] > 0.1)
        },
        {
            'name': 'MA20结束斜率 > 0.1 AND 持续时间 5-10周',
            'condition': (df_clean['ma20_slope_end'] > 0.1) & (df_clean['duration_weeks'] >= 5) & (df_clean['duration_weeks'] < 10)
        },
        {
            'name': 'MA20开始斜率 > 0.05 AND MA20结束斜率 > 0.1 AND 收敛度 < 0.07',
            'condition': (df_clean['ma20_slope_start'] > 0.05) & (df_clean['ma20_slope_end'] > 0.1) & (df_clean['avg_convergence'] < 0.07)
        }
    ]
    
    print(f"📊 组合条件效果分析:")
    print("-" * 80)
    
    for combo in combinations:
        subset = df_clean[combo['condition']]
        if len(subset) > 0:
            win_rate = subset['is_profitable_20w'].mean() * 100
            avg_return = subset['return_20w'].mean() * 100
            print(f"✅ {combo['name']}")
            print(f"   样本数: {len(subset)}, 胜率: {win_rate:.1f}%, 平均收益: {avg_return:.1f}%")
            print()

def ml_error_analysis(df):
    """使用机器学习分析错误模式"""
    if not ML_AVAILABLE:
        print("\n⚠️  机器学习库未安装，跳过ML错误分析")
        return
    
    print(f"\n" + "="*80)
    print("🤖 机器学习错误分析")
    print("="*80)
    
    df_clean = df.dropna()
    
    if len(df_clean) < 50:
        print("❌ 样本数量不足，无法进行机器学习分析")
        return
    
    # 准备数据
    features = ['avg_convergence', 'ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end', 'duration_weeks']
    X = df_clean[features]
    y = df_clean['is_profitable_20w']
    
    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 训练模型
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)
    
    # 特征重要性
    print("📊 特征重要性排序:")
    feature_importance = list(zip(features, model.feature_importances_))
    feature_importance.sort(key=lambda x: x[1], reverse=True)
    
    for i, (feature, importance) in enumerate(feature_importance, 1):
        print(f"   {i}. {feature}: {importance:.3f}")
    
    # 分析错误预测
    y_pred = model.predict(X_scaled)
    y_pred_proba = model.predict_proba(X_scaled)[:, 1]
    
    # 找出预测错误的案例
    wrong_predictions = df_clean[y_pred != y].copy()
    wrong_predictions['predicted_prob'] = y_pred_proba[y_pred != y]
    
    print(f"\n❌ 预测错误案例分析:")
    print(f"   总错误数: {len(wrong_predictions)}")
    print(f"   错误率: {len(wrong_predictions) / len(df_clean) * 100:.1f}%")
    
    # 分析错误案例的特征
    if len(wrong_predictions) > 0:
        print(f"\n📊 错误案例特征分析:")
        for feature, name in zip(features, ['平均收敛度', 'MA20斜率(开始)', 'MA60斜率(开始)', 'MA20斜率(结束)', 'MA60斜率(结束)', '持续时间']):
            mean_val = wrong_predictions[feature].mean()
            std_val = wrong_predictions[feature].std()
            print(f"   {name}: 均值={mean_val:.4f}, 标准差={std_val:.4f}")

def main():
    """主函数"""
    print("="*80)
    print("🔍 收敛时间段错误案例分析")
    print("="*80)
    
    # 加载数据
    df = load_convergence_data()
    if df is None:
        return
    
    # 分析错误模式
    analyze_error_patterns(df)
    
    # 找出高风险区域
    high_risk_zones = find_high_risk_zones(df)
    
    # 找出最优区域
    optimal_zones = find_optimal_zones(df)
    
    # 分析组合条件
    analyze_combined_conditions(df)
    
    # 机器学习错误分析
    ml_error_analysis(df)
    
    # 总结建议
    print(f"\n" + "="*80)
    print("💡 优化建议总结")
    print("="*80)
    
    print("🚨 应该避免的高风险区域:")
    for zone in high_risk_zones[:5]:  # 显示前5个最高风险区域
        print(f"   - {zone['feature']}: {zone['condition']} (胜率{zone['win_rate']:.1f}%)")
    
    print("\n✅ 应该重点关注的最优区域:")
    for zone in optimal_zones[:5]:  # 显示前5个最优区域
        print(f"   - {zone['feature']}: {zone['condition']} (胜率{zone['win_rate']:.1f}%)")
    
    print(f"\n🎯 基于分析的建议参数组合:")
    print(f"   1. MA20结束斜率 > 0.1 (最重要)")
    print(f"   2. MA20开始斜率 > 0.05")
    print(f"   3. 收敛度 < 0.07")
    print(f"   4. 持续时间 5-10周")
    print(f"   5. 避免MA20结束斜率 < -0.05的区域")

if __name__ == "__main__":
    main()
