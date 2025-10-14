#!/usr/bin/env python3
"""
基于收敛时间段的正确分析：每个收敛期一个样本，观察期后表现
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

def calculate_ma_slope(ma_values, periods=20):
    """计算MA斜率（20周变化率）"""
    if len(ma_values) < periods + 1:
        return np.nan
    
    current = ma_values[-1]
    past = ma_values[-(periods + 1)]
    
    if past == 0:
        return np.nan
    
    return (current - past) / past

def find_convergence_periods(stock_id, convergence_threshold=0.08, lookforward_weeks=40):
    """找到收敛时间段并观察后续表现"""
    data_loader = DataLoader()
    
    # 获取周线数据
    weekly_data = data_loader.load_klines(stock_id, term='weekly', adjust='qfq')
    
    if not weekly_data or len(weekly_data) < 100:
        return []
    
    # 提取价格数据和日期
    closes = [k['close'] for k in weekly_data if k.get('close')]
    dates = [k['date'] for k in weekly_data if k.get('date')]
    
    # 调试信息
    if len(closes) > 0:
        print(f"      📊 数据长度: {len(closes)}, 日期长度: {len(dates)}")
        if len(dates) > 0:
            print(f"      📅 日期范围: {dates[0]} 到 {dates[-1]}")
    
    # 计算移动平均线
    def rolling_mean(data, window):
        result = np.full(len(data), np.nan)
        for i in range(window - 1, len(data)):
            result[i] = np.mean(data[i - window + 1:i + 1])
        return result
    
    ma5 = rolling_mean(closes, 5)
    ma10 = rolling_mean(closes, 10)
    ma20 = rolling_mean(closes, 20)
    ma60 = rolling_mean(closes, 60)
    
    # 找到所有满足收敛条件的点
    convergence_points = []
    
    for i in range(60, len(closes)):
        if np.isnan(ma5[i]) or np.isnan(ma10[i]) or np.isnan(ma20[i]) or np.isnan(ma60[i]):
            continue
            
        ma_values = [ma5[i], ma10[i], ma20[i], ma60[i]]
        ma_max = max(ma_values)
        ma_min = min(ma_values)
        ma_convergence = (ma_max - ma_min) / closes[i]
        
        if ma_convergence < convergence_threshold and i < len(dates):
            convergence_points.append({
                'idx': i,
                'date': dates[i],
                'convergence': ma_convergence,
                'price': closes[i],
                'ma5': ma5[i],
                'ma10': ma10[i],
                'ma20': ma20[i],
                'ma60': ma60[i]
            })
    
    # 将连续的时间点合并为时间段
    convergence_periods = []
    if convergence_points:
        current_period = [convergence_points[0]]
        
        for i in range(1, len(convergence_points)):
            if convergence_points[i]['idx'] == convergence_points[i-1]['idx'] + 1:
                current_period.append(convergence_points[i])
            else:
                # 结束当前时间段，开始新时间段
                if len(current_period) >= 1:
                    start_point = current_period[0]
                    end_point = current_period[-1]
                    
                    # 计算时间段特征
                    start_idx = start_point['idx']
                    end_idx = end_point['idx']
                    
                    # 计算时间段内的平均特征
                    avg_convergence = sum(p['convergence'] for p in current_period) / len(current_period)
                    avg_price = sum(p['price'] for p in current_period) / len(current_period)
                    
                    # 计算时间段开始时的MA斜率（需要足够的历史数据）
                    if start_idx >= 80:
                        ma20_slope_start = calculate_ma_slope(ma20[:start_idx+1])
                        ma60_slope_start = calculate_ma_slope(ma60[:start_idx+1])
                    else:
                        ma20_slope_start = np.nan
                        ma60_slope_start = np.nan
                    
                    # 计算时间段结束时的MA斜率
                    if end_idx >= 80:
                        ma20_slope_end = calculate_ma_slope(ma20[:end_idx+1])
                        ma60_slope_end = calculate_ma_slope(ma60[:end_idx+1])
                    else:
                        ma20_slope_end = np.nan
                        ma60_slope_end = np.nan
                    
                    # 观察收敛期结束后的表现
                    future_start_idx = end_idx + 1
                    if future_start_idx + lookforward_weeks < len(closes):
                        # 计算未来N周的收益
                        future_prices = closes[future_start_idx:future_start_idx + lookforward_weeks + 1]
                        if len(future_prices) >= lookforward_weeks + 1:
                            # 计算未来20周和40周的收益
                            return_20w = (future_prices[20] - closes[end_idx]) / closes[end_idx] if len(future_prices) > 20 else np.nan
                            return_40w = (future_prices[40] - closes[end_idx]) / closes[end_idx] if len(future_prices) > 40 else np.nan
                            
                            # 计算未来最大收益
                            max_future_price = max(future_prices)
                            max_return = (max_future_price - closes[end_idx]) / closes[end_idx]
                            
                            # 定义标签：20周后是否盈利
                            is_profitable_20w = 1 if return_20w > 0 else 0
                            is_profitable_40w = 1 if return_40w > 0 else 0
                            
                            convergence_periods.append({
                                'stock_id': stock_id,
                                'start_date': start_point['date'],
                                'end_date': end_point['date'],
                                'start_idx': start_idx,
                                'end_idx': end_idx,
                                'duration_weeks': len(current_period),
                                'avg_convergence': avg_convergence,
                                'avg_price': avg_price,
                                'ma20_slope_start': ma20_slope_start,
                                'ma60_slope_start': ma60_slope_start,
                                'ma20_slope_end': ma20_slope_end,
                                'ma60_slope_end': ma60_slope_end,
                                'start_price': start_point['price'],
                                'end_price': end_point['price'],
                                'period_price_change': (end_point['price'] - start_point['price']) / start_point['price'],
                                'return_20w': return_20w,
                                'return_40w': return_40w,
                                'max_return': max_return,
                                'is_profitable_20w': is_profitable_20w,
                                'is_profitable_40w': is_profitable_40w,
                                'future_max_price': max_future_price
                            })
                
                current_period = [convergence_points[i]]
        
        # 处理最后一个时间段
        if len(current_period) >= 1:
            start_point = current_period[0]
            end_point = current_period[-1]
            
            start_idx = start_point['idx']
            end_idx = end_point['idx']
            
            avg_convergence = sum(p['convergence'] for p in current_period) / len(current_period)
            avg_price = sum(p['price'] for p in current_period) / len(current_period)
            
            if start_idx >= 80:
                ma20_slope_start = calculate_ma_slope(ma20[:start_idx+1])
                ma60_slope_start = calculate_ma_slope(ma60[:start_idx+1])
            else:
                ma20_slope_start = np.nan
                ma60_slope_start = np.nan
            
            if end_idx >= 80:
                ma20_slope_end = calculate_ma_slope(ma20[:end_idx+1])
                ma60_slope_end = calculate_ma_slope(ma60[:end_idx+1])
            else:
                ma20_slope_end = np.nan
                ma60_slope_end = np.nan
            
            # 观察收敛期结束后的表现
            future_start_idx = end_idx + 1
            if future_start_idx + lookforward_weeks < len(closes):
                future_prices = closes[future_start_idx:future_start_idx + lookforward_weeks + 1]
                if len(future_prices) >= lookforward_weeks + 1:
                    return_20w = (future_prices[20] - closes[end_idx]) / closes[end_idx] if len(future_prices) > 20 else np.nan
                    return_40w = (future_prices[40] - closes[end_idx]) / closes[end_idx] if len(future_prices) > 40 else np.nan
                    
                    max_future_price = max(future_prices)
                    max_return = (max_future_price - closes[end_idx]) / closes[end_idx]
                    
                    is_profitable_20w = 1 if return_20w > 0 else 0
                    is_profitable_40w = 1 if return_40w > 0 else 0
                    
                    convergence_periods.append({
                        'stock_id': stock_id,
                        'start_date': start_point['date'],
                        'end_date': end_point['date'],
                        'start_idx': start_idx,
                        'end_idx': end_idx,
                        'duration_weeks': len(current_period),
                        'avg_convergence': avg_convergence,
                        'avg_price': avg_price,
                        'ma20_slope_start': ma20_slope_start,
                        'ma60_slope_start': ma60_slope_start,
                        'ma20_slope_end': ma20_slope_end,
                        'ma60_slope_end': ma60_slope_end,
                        'start_price': start_point['price'],
                        'end_price': end_point['price'],
                        'period_price_change': (end_point['price'] - start_point['price']) / start_point['price'],
                        'return_20w': return_20w,
                        'return_40w': return_40w,
                        'max_return': max_return,
                        'is_profitable_20w': is_profitable_20w,
                        'is_profitable_40w': is_profitable_40w,
                        'future_max_price': max_future_price
                    })
    
    return convergence_periods

def collect_all_convergence_periods():
    """收集所有股票的收敛时间段数据"""
    # 扩大股票池，增加样本量
    test_stocks = [
        # 银行股
        "000001.SZ", "600036.SH", "600000.SH", "000002.SZ", "600016.SH",
        # 地产股
        "000002.SZ", "000069.SZ", "001979.SZ", "600048.SH", "000656.SZ",
        # 白酒股
        "000858.SZ", "600519.SH", "000596.SZ", "600809.SH", "000799.SZ",
        # 科技股
        "000725.SZ", "002415.SZ", "000063.SZ", "002230.SZ", "300059.SZ",
        # 医药股
        "600276.SH", "000661.SZ", "300015.SZ", "002007.SZ", "600196.SH",
        # 其他行业
        "600028.SH", "600900.SH", "002594.SZ", "300750.SZ"
    ]
    
    # 去重
    test_stocks = list(set(test_stocks))
    
    all_periods = []
    
    print("📊 收集收敛时间段数据...")
    for i, stock_id in enumerate(test_stocks, 1):
        print(f"   [{i}/{len(test_stocks)}] 处理 {stock_id}...")
        periods = find_convergence_periods(stock_id, convergence_threshold=0.10, lookforward_weeks=40)
        all_periods.extend(periods)
        print(f"      找到 {len(periods)} 个收敛时间段")
    
    return all_periods

def analyze_convergence_periods(df):
    """分析收敛时间段的特征和后续表现"""
    print("\n" + "="*80)
    print("📊 收敛时间段分析结果")
    print("="*80)
    
    # 过滤掉包含NaN的数据
    df_clean = df.dropna()
    
    print(f"📈 总收敛时间段数: {len(df_clean)}")
    print(f"✅ 20周后盈利: {df_clean['is_profitable_20w'].sum()}")
    print(f"❌ 20周后亏损: {len(df_clean) - df_clean['is_profitable_20w'].sum()}")
    print(f"🎯 20周胜率: {df_clean['is_profitable_20w'].mean()*100:.1f}%")
    
    print(f"✅ 40周后盈利: {df_clean['is_profitable_40w'].sum()}")
    print(f"❌ 40周后亏损: {len(df_clean) - df_clean['is_profitable_40w'].sum()}")
    print(f"🎯 40周胜率: {df_clean['is_profitable_40w'].mean()*100:.1f}%")
    
    # 分析平均收益
    print(f"\n📊 收益分析:")
    print(f"   20周平均收益: {df_clean['return_20w'].mean()*100:.2f}%")
    print(f"   40周平均收益: {df_clean['return_40w'].mean()*100:.2f}%")
    print(f"   最大平均收益: {df_clean['max_return'].mean()*100:.2f}%")
    
    # 分析收敛期内的价格变化
    print(f"\n📊 收敛期内表现:")
    print(f"   收敛期内平均价格变化: {df_clean['period_price_change'].mean()*100:.2f}%")
    print(f"   收敛期平均持续时间: {df_clean['duration_weeks'].mean():.1f}周")
    
    # 分别分析盈利和亏损样本的特征
    profitable_20w = df_clean[df_clean['is_profitable_20w'] == 1]
    unprofitable_20w = df_clean[df_clean['is_profitable_20w'] == 0]
    
    print(f"\n📊 20周后盈利vs亏损特征对比:")
    print("-" * 60)
    
    features = ['avg_convergence', 'ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end', 'duration_weeks']
    feature_names = ['平均收敛度', 'MA20斜率(开始)', 'MA60斜率(开始)', 'MA20斜率(结束)', 'MA60斜率(结束)', '持续时间']
    
    for feature, name in zip(features, feature_names):
        if feature in df_clean.columns:
            prof_mean = profitable_20w[feature].mean()
            unprof_mean = unprofitable_20w[feature].mean()
            prof_std = profitable_20w[feature].std()
            unprof_std = unprofitable_20w[feature].std()
            
            print(f"\n{name}:")
            print(f"   盈利样本: 均值={prof_mean:.4f}, 标准差={prof_std:.4f}")
            print(f"   亏损样本: 均值={unprof_mean:.4f}, 标准差={unprof_std:.4f}")
            print(f"   差异: {prof_mean - unprof_mean:.4f}")
            
            # 分析不同区间的胜率
            if feature == 'avg_convergence':
                print(f"   收敛度区间胜率分析:")
                for threshold in [0.03, 0.05, 0.07, 0.08]:
                    subset = df_clean[df_clean[feature] < threshold]
                    if len(subset) > 0:
                        win_rate = subset['is_profitable_20w'].mean() * 100
                        avg_return = subset['return_20w'].mean() * 100
                        print(f"     <{threshold}: {len(subset)}个样本, 胜率{win_rate:.1f}%, 平均收益{avg_return:.1f}%")
            
            elif feature in ['ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end']:
                print(f"   斜率区间胜率分析:")
                for slope_range in [(-0.1, -0.05), (-0.05, 0), (0, 0.05), (0.05, 0.1), (0.1, 0.2)]:
                    subset = df_clean[(df_clean[feature] >= slope_range[0]) & (df_clean[feature] < slope_range[1])]
                    if len(subset) > 0:
                        win_rate = subset['is_profitable_20w'].mean() * 100
                        avg_return = subset['return_20w'].mean() * 100
                        print(f"     {slope_range[0]}~{slope_range[1]}: {len(subset)}个样本, 胜率{win_rate:.1f}%, 平均收益{avg_return:.1f}%")
            
            elif feature == 'duration_weeks':
                print(f"   持续时间区间胜率分析:")
                for duration_range in [(1, 5), (5, 10), (10, 20), (20, 50)]:
                    subset = df_clean[(df_clean[feature] >= duration_range[0]) & (df_clean[feature] < duration_range[1])]
                    if len(subset) > 0:
                        win_rate = subset['is_profitable_20w'].mean() * 100
                        avg_return = subset['return_20w'].mean() * 100
                        print(f"     {duration_range[0]}~{duration_range[1]}周: {len(subset)}个样本, 胜率{win_rate:.1f}%, 平均收益{avg_return:.1f}%")

def ml_analysis_convergence_periods(df):
    """对收敛时间段进行机器学习分析"""
    if not ML_AVAILABLE:
        print("\n⚠️  机器学习库未安装，跳过ML分析")
        return
    
    print("\n" + "="*80)
    print("🤖 收敛时间段机器学习分析")
    print("="*80)
    
    # 准备数据
    df_clean = df.dropna()
    
    if len(df_clean) < 30:
        print("❌ 样本数量不足，无法进行机器学习分析")
        return
    
    # 特征选择
    features = ['avg_convergence', 'ma20_slope_start', 'ma60_slope_start', 'ma20_slope_end', 'ma60_slope_end', 'duration_weeks']
    X = df_clean[features]
    y = df_clean['is_profitable_20w']  # 使用20周后的表现作为标签
    
    print(f"📊 训练样本数: {len(X)}")
    print(f"🎯 特征: {features}")
    print(f"📈 标签: 20周后是否盈利")
    
    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 分割训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42)
    
    # 训练多个模型
    models = {
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(random_state=42),
        'XGBoost': xgb.XGBClassifier(random_state=42, eval_metric='logloss')
    }
    
    best_model = None
    best_score = 0
    
    for name, model in models.items():
        print(f"\n🔍 训练 {name}...")
        
        # 训练模型
        model.fit(X_train, y_train)
        
        # 预测
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # 评估
        accuracy = model.score(X_test, y_test)
        auc = roc_auc_score(y_test, y_pred_proba)
        
        print(f"   准确率: {accuracy:.3f}")
        print(f"   AUC: {auc:.3f}")
        
        if auc > best_score:
            best_score = auc
            best_model = model
        
        # 特征重要性
        if hasattr(model, 'feature_importances_'):
            print(f"   特征重要性:")
            for i, feature in enumerate(features):
                importance = model.feature_importances_[i]
                print(f"     {feature}: {importance:.3f}")
    
    # 使用最佳模型进行详细分析
    if best_model:
        print(f"\n🏆 最佳模型分析:")
        print("-" * 60)
        
        # 特征重要性
        if hasattr(best_model, 'feature_importances_'):
            print("📊 特征重要性排序:")
            feature_importance = list(zip(features, best_model.feature_importances_))
            feature_importance.sort(key=lambda x: x[1], reverse=True)
            
            for i, (feature, importance) in enumerate(feature_importance, 1):
                print(f"   {i}. {feature}: {importance:.3f}")
        
        # 交叉验证
        cv_scores = cross_val_score(best_model, X_scaled, y, cv=5, scoring='roc_auc')
        print(f"\n📈 5折交叉验证AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

def main():
    """主函数"""
    print("="*80)
    print("🎯 基于收敛时间段的正确分析：每个收敛期一个样本")
    print("="*80)
    
    # 收集数据
    all_periods = collect_all_convergence_periods()
    
    if not all_periods:
        print("❌ 未找到任何收敛时间段数据")
        return
    
    # 转换为DataFrame
    df = pd.DataFrame(all_periods)
    
    print(f"\n📊 数据概览:")
    print(f"   总收敛时间段数: {len(df)}")
    print(f"   20周后盈利: {df['is_profitable_20w'].sum()}")
    print(f"   20周后亏损: {len(df) - df['is_profitable_20w'].sum()}")
    print(f"   20周胜率: {df['is_profitable_20w'].mean()*100:.1f}%")
    
    # 分析收敛时间段
    analyze_convergence_periods(df)
    
    # 机器学习分析
    ml_analysis_convergence_periods(df)
    
    # 保存数据
    output_file = "/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/convergence_periods_analysis.csv"
    df.to_csv(output_file, index=False)
    print(f"\n💾 数据已保存到: {output_file}")

if __name__ == "__main__":
    main()
