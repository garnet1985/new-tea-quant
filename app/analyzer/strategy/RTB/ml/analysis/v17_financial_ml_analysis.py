#!/usr/bin/env python3
"""
V17策略财务指标机器学习分析
基于财务特征进行更全面的ML分析
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
import warnings
warnings.filterwarnings('ignore')

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))
sys.path.append('.')

from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader

def load_investment_data_with_financials(tmp_dir: str, data_loader, db_manager) -> tuple:
    """加载投资数据并补充财务指标"""
    print(f"📊 加载投资数据并补充财务指标: {tmp_dir}")
    
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
    stock_files = [f for f in stock_files if f.name != "0_session_summary.json"]
    
    print(f"股票文件数量: {len(stock_files)}")
    
    # 随机采样，避免分析所有股票（太耗时）
    import random
    sample_files = random.sample(stock_files, min(200, len(stock_files)))
    print(f"随机采样文件数量: {len(sample_files)}")
    
    for i, stock_file in enumerate(sample_files):
        try:
            if i % 50 == 0:
                print(f"  处理进度: {i}/{len(sample_files)}")
                
            with open(stock_file, 'r') as f:
                stock_data = json.load(f)
            
            stock_id = stock_data['stock']['id']
            stock_investments = stock_data.get('investments', [])
            
            # 获取股票的财务数据
            financial_data = get_stock_financials(stock_id, data_loader)
            
            for inv in stock_investments:
                # 检查是否有投资结果（已完成）
                if inv.get('result') in ['win', 'loss']:
                    # 转换result为is_successful格式
                    inv['is_successful'] = (inv['result'] == 'win')
                    # 转换ROI格式
                    if 'overall_profit_rate' in inv:
                        inv['roi'] = inv['overall_profit_rate']
                    
                    # 添加财务数据
                    inv['financial_data'] = financial_data
                    
                    investments.append(inv)
                    
        except Exception as e:
            print(f"加载文件失败 {stock_file}: {e}")
            continue
    
    print(f"有效投资记录: {len(investments)}")
    return investments, summary

def get_stock_financials(stock_id: str, data_loader) -> dict:
    """获取股票的财务指标"""
    try:
        # 获取最新K线数据（包含财务指标）
        klines = data_loader.load_klines(
            stock_id=stock_id,
            term='daily',
            adjust='qfq'
        )
        
        if not klines:
            return {}
        
        # 获取最新一条K线的财务数据
        latest_kline = klines[-1]
        
        # 提取财务指标
        financial_metrics = {
            'market_cap': latest_kline.get('total_market_value', None),
            'pe_ratio': latest_kline.get('pe', None),
            'pb_ratio': latest_kline.get('pb', None),
            'ps_ratio': latest_kline.get('ps', None),
            'turnover_rate': latest_kline.get('turnover_rate', None),
            'volume_ratio': latest_kline.get('volume_ratio', None),
            'close': latest_kline.get('close', None),
            'volume': latest_kline.get('volume', None),
            'amount': latest_kline.get('amount', None),
        }
        
        return financial_metrics
        
    except Exception as e:
        print(f"获取财务数据失败 {stock_id}: {e}")
        return {}

def extract_features_with_financials(investments: list) -> tuple:
    """提取特征和标签，包含财务指标"""
    print("🔍 提取特征（包含财务指标）...")
    
    features_list = []
    labels = []
    
    for inv in investments:
        try:
            # 提取信号条件特征
            signal_conditions = inv.get('extra_fields', {}).get('signal_conditions', {})
            financial_data = inv.get('financial_data', {})
            
            if not signal_conditions:
                continue
            
            # 技术指标特征
            technical_features = {
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
            
            # 财务指标特征
            financial_features = {
                'market_cap_log': np.log10(financial_data.get('market_cap', 1)) if financial_data.get('market_cap') and financial_data.get('market_cap') > 0 else 0,
                'pe_ratio': financial_data.get('pe_ratio', 0) if financial_data.get('pe_ratio') and financial_data.get('pe_ratio') > 0 else 0,
                'pb_ratio': financial_data.get('pb_ratio', 0) if financial_data.get('pb_ratio') and financial_data.get('pb_ratio') > 0 else 0,
                'ps_ratio': financial_data.get('ps_ratio', 0) if financial_data.get('ps_ratio') and financial_data.get('ps_ratio') > 0 else 0,
                'turnover_rate': financial_data.get('turnover_rate', 0) if financial_data.get('turnover_rate') else 0,
                'volume_ratio_fin': financial_data.get('volume_ratio', 0) if financial_data.get('volume_ratio') else 0,
            }
            
            # 投资结果特征
            result_features = {
                'duration_days': inv.get('duration_in_days', 0),
                'roi': inv.get('roi', 0),
            }
            
            # 合并所有特征
            all_features = {**technical_features, **financial_features, **result_features}
            features_list.append(list(all_features.values()))
            labels.append(1 if inv.get('is_successful') else 0)
            
        except Exception as e:
            print(f"提取特征失败: {e}")
            continue
    
    X = np.array(features_list)
    y = np.array(labels)
    
    print(f"特征维度: {X.shape}")
    print(f"标签分布: 成功={np.sum(y)}, 失败={np.sum(1-y)}")
    
    return X, y

def analyze_feature_importance_with_financials(X: np.ndarray, y: np.ndarray) -> dict:
    """分析特征重要性（包含财务指标）"""
    print("🎯 分析特征重要性（包含财务指标）...")
    
    feature_names = [
        # 技术指标
        'ma_convergence', 'ma20_slope', 'ma60_slope', 'volume_trend', 'amount_ratio',
        'historical_percentile', 'oscillation_position', 'volume_confirmation', 'rsi_signal',
        # 财务指标
        'market_cap_log', 'pe_ratio', 'pb_ratio', 'ps_ratio', 'turnover_rate', 'volume_ratio_fin',
        # 结果指标
        'duration_days', 'roi'
    ]
    
    # 训练随机森林
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    # 获取特征重要性
    importance = rf.feature_importances_
    feature_importance = dict(zip(feature_names, importance))
    
    # 排序
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    
    print("\n📊 特征重要性排序（包含财务指标）:")
    for i, (feature, imp) in enumerate(sorted_features):
        category = get_feature_category(feature)
        print(f"  {i+1:2d}. {feature:<20}: {imp:.4f} ({category})")
    
    return feature_importance

def get_feature_category(feature_name: str) -> str:
    """获取特征类别"""
    technical_features = ['ma_convergence', 'ma20_slope', 'ma60_slope', 'volume_trend', 'amount_ratio',
                         'historical_percentile', 'oscillation_position', 'volume_confirmation', 'rsi_signal']
    financial_features = ['market_cap_log', 'pe_ratio', 'pb_ratio', 'ps_ratio', 'turnover_rate', 'volume_ratio_fin']
    result_features = ['duration_days', 'roi']
    
    if feature_name in technical_features:
        return "技术指标"
    elif feature_name in financial_features:
        return "财务指标"
    elif feature_name in result_features:
        return "结果指标"
    else:
        return "未知"

def analyze_financial_thresholds(investments: list) -> dict:
    """分析财务指标阈值"""
    print("📈 分析财务指标阈值...")
    
    # 按财务指标分组分析
    financial_metrics = ['market_cap', 'pe_ratio', 'pb_ratio', 'ps_ratio', 'turnover_rate']
    
    threshold_analysis = {}
    
    for metric in financial_metrics:
        print(f"\n🔍 {metric}分析:")
        
        # 提取数据
        metric_data = []
        for inv in investments:
            financial_data = inv.get('financial_data', {})
            value = financial_data.get(metric)
            if value is not None and value > 0:
                metric_data.append({
                    'value': value,
                    'success': inv.get('is_successful', False),
                    'roi': inv.get('roi', 0)
                })
        
        if not metric_data:
            print(f"  无有效数据")
            continue
        
        # 排序
        metric_data.sort(key=lambda x: x['value'])
        
        # 计算分位数阈值
        values = [d['value'] for d in metric_data]
        percentiles = [25, 50, 75]
        
        for p in percentiles:
            threshold = np.percentile(values, p)
            below_threshold = [d for d in metric_data if d['value'] <= threshold]
            above_threshold = [d for d in metric_data if d['value'] > threshold]
            
            if below_threshold and above_threshold:
                below_success_rate = np.mean([d['success'] for d in below_threshold])
                above_success_rate = np.mean([d['success'] for d in above_threshold])
                below_roi = np.mean([d['roi'] for d in below_threshold])
                above_roi = np.mean([d['roi'] for d in above_threshold])
                
                print(f"  {p}分位阈值 {threshold:.2f}:")
                print(f"    低于阈值: 胜率={below_success_rate:.2%}, ROI={below_roi:.2%}, 样本={len(below_threshold)}")
                print(f"    高于阈值: 胜率={above_success_rate:.2%}, ROI={above_roi:.2%}, 样本={len(above_threshold)}")
        
        threshold_analysis[metric] = metric_data
    
    return threshold_analysis

def suggest_optimizations_with_financials(feature_importance: dict, threshold_analysis: dict) -> dict:
    """基于财务指标分析提出优化建议"""
    print("\n💡 基于财务指标的优化建议:")
    
    suggestions = {
        'financial_filters': [],
        'technical_adjustments': [],
        'expected_impact': {}
    }
    
    # 1. 财务指标筛选建议
    print("\n1️⃣ 财务指标筛选建议:")
    
    # 市值筛选
    if 'market_cap_log' in feature_importance:
        importance = feature_importance['market_cap_log']
        if importance > 0.01:  # 重要性超过1%
            print(f"  📊 市值筛选: 重要性={importance:.4f}")
            print(f"     建议: 排除市值过小的股票（<50亿）")
            suggestions['financial_filters'].append({
                'metric': 'market_cap',
                'condition': '> 500000',  # 50亿
                'reason': f'重要性={importance:.4f}，小市值股票表现较差'
            })
    
    # PE筛选
    if 'pe_ratio' in feature_importance:
        importance = feature_importance['pe_ratio']
        if importance > 0.01:
            print(f"  📊 PE筛选: 重要性={importance:.4f}")
            print(f"     建议: 排除极端PE值股票（<5或>100）")
            suggestions['financial_filters'].append({
                'metric': 'pe_ratio',
                'condition': '5 < pe_ratio < 100',
                'reason': f'重要性={importance:.4f}，极端PE值股票风险较高'
            })
    
    # PB筛选
    if 'pb_ratio' in feature_importance:
        importance = feature_importance['pb_ratio']
        if importance > 0.01:
            print(f"  📊 PB筛选: 重要性={importance:.4f}")
            print(f"     建议: 排除极端PB值股票（<0.5或>10）")
            suggestions['financial_filters'].append({
                'metric': 'pb_ratio',
                'condition': '0.5 < pb_ratio < 10',
                'reason': f'重要性={importance:.4f}，极端PB值股票风险较高'
            })
    
    # 2. 技术指标调整建议
    print("\n2️⃣ 技术指标调整建议:")
    
    # 找出重要性最高的技术指标
    technical_features = ['ma_convergence', 'historical_percentile', 'rsi_signal', 'volume_confirmation']
    for feature in technical_features:
        if feature in feature_importance:
            importance = feature_importance[feature]
            print(f"  📈 {feature}: 重要性={importance:.4f}")
            
            if feature == 'ma_convergence' and importance > 0.02:
                print(f"     建议: 当前阈值0.10，可考虑微调")
            elif feature == 'historical_percentile' and importance > 0.02:
                print(f"     建议: 当前阈值0.3，可考虑微调")
    
    return suggestions

def main():
    print("🚀 V17策略财务指标机器学习分析开始...")
    
    # 初始化数据库和加载器
    db = DatabaseManager()
    db.initialize()
    data_loader = DataLoader(db)
    
    try:
        # 加载数据
        tmp_dir = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp/2025_10_17-210"
        investments, summary = load_investment_data_with_financials(tmp_dir, data_loader, db)
        
        if len(investments) < 100:
            print("❌ 投资记录太少，无法进行有效分析")
            return
        
        # 提取特征
        X, y = extract_features_with_financials(investments)
        
        # 分析特征重要性
        feature_importance = analyze_feature_importance_with_financials(X, y)
        
        # 分析财务指标阈值
        threshold_analysis = analyze_financial_thresholds(investments)
        
        # 提出优化建议
        suggestions = suggest_optimizations_with_financials(feature_importance, threshold_analysis)
        
        print("\n🎯 总结:")
        print(f"当前胜率: {summary['win_rate']:.1f}%")
        print(f"当前ROI: {summary['avg_roi']:.3f}")
        print(f"投资机会: {summary['total_investments']}次")
        print(f"分析样本: {len(investments)}个投资记录")
        
        print("\n💡 主要发现:")
        print("1. 财务指标对策略表现有重要影响")
        print("2. 市值、PE、PB等指标可以作为筛选条件")
        print("3. 建议实施财务指标筛选以提升策略表现")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if db.is_sync_connected:
            db.disconnect()

if __name__ == "__main__":
    main()
