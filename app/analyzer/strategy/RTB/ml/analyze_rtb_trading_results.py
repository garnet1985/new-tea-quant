#!/usr/bin/env python3
"""
分析RTB ML增强版本的交易结果
提取成功和失败案例的特征，进行机器学习分析
"""

import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

def load_trading_results():
    """加载RTB ML增强版本的交易结果"""
    results_dir = Path("/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp/2025_10_21-257")
    
    if not results_dir.exists():
        print(f"❌ 结果目录不存在: {results_dir}")
        return None
    
    # 加载会话汇总
    summary_file = results_dir / "0_session_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        print(f"📊 会话汇总:")
        print(f"   总投资次数: {summary.get('total_investments', 0)}")
        print(f"   成功次数: {summary.get('total_win_investments', 0)}")
        print(f"   失败次数: {summary.get('total_loss_investments', 0)}")
        print(f"   胜率: {summary.get('win_rate', 0):.1f}%")
        print(f"   平均ROI: {summary.get('avg_roi', 0):.1%}")
    
    # 加载所有交易记录
    trading_data = []
    
    for json_file in results_dir.glob("*.json"):
        if json_file.name == "0_session_summary.json":
            continue
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            
            stock_id = stock_data.get('stock', {}).get('id', '')
            stock_name = stock_data.get('stock', {}).get('name', '')
            investments = stock_data.get('investments', [])
            
            for investment in investments:
                if 'extra_fields' not in investment:
                    continue
                
                features = investment['extra_fields'].get('features', {})
                financial_indicators = investment['extra_fields'].get('financial_indicators', {})
                
                # 构建交易记录
                record = {
                    'stock_id': stock_id,
                    'stock_name': stock_name,
                    'result': investment.get('result', ''),
                    'start_date': investment.get('start_date', ''),
                    'end_date': investment.get('end_date', ''),
                    'duration_in_days': investment.get('duration_in_days', 0),
                    'overall_profit_rate': investment.get('overall_profit_rate', 0),
                    'purchase_price': investment.get('purchase_price', 0),
                }
                
                # 添加ML特征
                record.update(features)
                
                # 添加财务指标
                record.update({
                    'market_cap': financial_indicators.get('market_cap', 0),
                    'pe_ratio': financial_indicators.get('pe_ratio', 0),
                    'pb_ratio': financial_indicators.get('pb_ratio', 0),
                    'ps_ratio': financial_indicators.get('ps_ratio', 0),
                    'turnover_rate': financial_indicators.get('turnover_rate', 0),
                })
                
                trading_data.append(record)
                
        except Exception as e:
            print(f"❌ 读取文件 {json_file.name} 失败: {e}")
    
    print(f"✅ 成功加载 {len(trading_data)} 条交易记录")
    return pd.DataFrame(trading_data)

def prepare_ml_data(df):
    """准备机器学习数据"""
    if df.empty:
        return None, None
    
    # 选择特征列
    feature_cols = [
        'volatility', 'volume_ratio_after', 'ma_convergence', 'price_vs_ma10',
        'price_vs_ma20', 'price_momentum_10', 'price_vs_ma5', 'price_vs_ma60',
        'monthly_drop_rate', 'volume_ratio_before', 'ma5_slope', 'ma10_slope',
        'ma20_slope', 'ma60_slope', 'ma_slope_trend', 'rsi', 'price_percentile',
        'market_cap', 'pe_ratio', 'pb_ratio', 'ps_ratio', 'turnover_rate'
    ]
    
    # 过滤存在的特征列
    available_features = [col for col in feature_cols if col in df.columns]
    print(f"📊 可用特征: {len(available_features)} 个")
    
    # 准备特征和目标变量
    X = df[available_features].copy()
    y = (df['result'] == 'win').astype(int)
    
    # 处理缺失值
    X = X.fillna(0)
    
    print(f"📊 数据统计:")
    print(f"   总样本数: {len(X)}")
    print(f"   成功案例: {y.sum()}")
    print(f"   失败案例: {len(y) - y.sum()}")
    print(f"   成功率: {y.mean():.1%}")
    
    return X, y, available_features

def train_models(X, y, feature_cols):
    """训练机器学习模型"""
    # 分割数据
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 标准化特征
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000)
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\n🤖 训练 {name}...")
        
        if name == 'Logistic Regression':
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # 计算指标
        auc = roc_auc_score(y_test, y_pred_proba)
        accuracy = (y_pred == y_test).mean()
        
        results[name] = {
            'model': model,
            'auc': auc,
            'accuracy': accuracy,
            'y_test': y_test,
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba
        }
        
        print(f"   AUC: {auc:.3f}")
        print(f"   准确率: {accuracy:.1%}")
    
    return results, feature_cols, scaler

def analyze_feature_importance(results, feature_cols):
    """分析特征重要性"""
    print(f"\n🔍 特征重要性分析:")
    
    # 从树模型获取特征重要性
    tree_models = ['Random Forest', 'Gradient Boosting']
    
    for model_name in tree_models:
        if model_name in results:
            model = results[model_name]['model']
            importance = model.feature_importances_
            
            # 创建特征重要性DataFrame
            importance_df = pd.DataFrame({
                'feature': feature_cols,
                'importance': importance
            }).sort_values('importance', ascending=False)
            
            print(f"\n📊 {model_name} 特征重要性 (Top 10):")
            for i, row in importance_df.head(10).iterrows():
                print(f"   {row['feature']}: {row['importance']:.4f}")

def compare_success_failure(df, feature_cols):
    """比较成功和失败案例的特征差异"""
    print(f"\n📊 成功vs失败案例特征对比:")
    
    success_cases = df[df['result'] == 'win']
    failure_cases = df[df['result'] == 'loss']
    
    print(f"   成功案例数: {len(success_cases)}")
    print(f"   失败案例数: {len(failure_cases)}")
    
    comparison_results = []
    
    for feature in feature_cols:
        if feature in df.columns:
            success_mean = success_cases[feature].mean()
            failure_mean = failure_cases[feature].mean()
            diff = success_mean - failure_mean
            
            comparison_results.append({
                'feature': feature,
                'success_mean': success_mean,
                'failure_mean': failure_mean,
                'difference': diff,
                'abs_difference': abs(diff)
            })
    
    # 按差异绝对值排序
    comparison_df = pd.DataFrame(comparison_results).sort_values('abs_difference', ascending=False)
    
    print(f"\n🔍 特征差异分析 (Top 10):")
    for _, row in comparison_df.head(10).iterrows():
        print(f"   {row['feature']}:")
        print(f"     成功案例均值: {row['success_mean']:.4f}")
        print(f"     失败案例均值: {row['failure_mean']:.4f}")
        print(f"     差异: {row['difference']:.4f}")
        print()

def generate_visualizations(df, results, feature_cols):
    """生成可视化图表"""
    print(f"\n📈 生成可视化图表...")
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('RTB ML Enhanced Trading Results Analysis', fontsize=16, fontweight='bold')
    
    # 1. 结果分布
    result_counts = df['result'].value_counts()
    axes[0, 0].pie(result_counts.values, labels=result_counts.index, autopct='%1.1f%%', startangle=90)
    axes[0, 0].set_title('Trading Results Distribution')
    
    # 2. 收益率分布
    axes[0, 1].hist(df['overall_profit_rate'], bins=50, alpha=0.7, edgecolor='black')
    axes[0, 1].axvline(0, color='red', linestyle='--', label='Break-even')
    axes[0, 1].set_title('Profit Rate Distribution')
    axes[0, 1].set_xlabel('Profit Rate')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].legend()
    
    # 3. 投资时长分布
    success_cases = df[df['result'] == 'win']
    failure_cases = df[df['result'] == 'loss']
    
    axes[1, 0].hist([success_cases['duration_in_days'], failure_cases['duration_in_days']], 
                   bins=30, alpha=0.7, label=['Success', 'Failure'], edgecolor='black')
    axes[1, 0].set_title('Investment Duration Distribution')
    axes[1, 0].set_xlabel('Duration (Days)')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].legend()
    
    # 4. 模型性能比较
    model_names = list(results.keys())
    auc_scores = [results[name]['auc'] for name in model_names]
    
    bars = axes[1, 1].bar(model_names, auc_scores, color=['skyblue', 'lightgreen', 'lightcoral'])
    axes[1, 1].set_title('Model Performance (AUC)')
    axes[1, 1].set_ylabel('AUC Score')
    axes[1, 1].set_ylim(0, 1)
    
    # 添加数值标签
    for bar, score in zip(bars, auc_scores):
        axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                       f'{score:.3f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig('/Users/garnet/Desktop/stocks-py/rtb_ml_enhanced_analysis.png', dpi=300, bbox_inches='tight')
    print(f"✅ 图表已保存: rtb_ml_enhanced_analysis.png")

def main():
    """主函数"""
    print("🚀 开始分析RTB ML增强版本交易结果...")
    
    # 1. 加载交易结果
    df = load_trading_results()
    if df is None or df.empty:
        print("❌ 无法加载交易结果")
        return
    
    # 2. 准备机器学习数据
    X, y, feature_cols = prepare_ml_data(df)
    if X is None:
        print("❌ 无法准备机器学习数据")
        return
    
    # 3. 训练模型
    results, feature_cols, scaler = train_models(X, y, feature_cols)
    
    # 4. 分析特征重要性
    analyze_feature_importance(results, feature_cols)
    
    # 5. 比较成功失败案例
    compare_success_failure(df, feature_cols)
    
    # 6. 生成可视化
    generate_visualizations(df, results, feature_cols)
    
    print(f"\n✅ RTB ML增强版本交易结果分析完成!")
    print(f"📊 关键发现:")
    print(f"   - 总交易次数: {len(df)}")
    print(f"   - 成功率: {y.mean():.1%}")
    print(f"   - 最佳模型AUC: {max([results[name]['auc'] for name in results]):.3f}")

if __name__ == "__main__":
    main()
