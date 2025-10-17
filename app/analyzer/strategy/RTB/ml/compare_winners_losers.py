#!/usr/bin/env python3
"""
深度对比：止损组 vs 达到20%组
找出两组之间的关键差异特征
"""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader

print('='*80)
print('深度对比：止损组 vs 达到20%组')
print('='*80)

# ============================================================================
# 加载最终验证结果
# ============================================================================

print('\n📊 加载验证数据...')

results_file = os.path.join(os.path.dirname(__file__), '../requirements/FINAL_RESULTS.csv')
trades_df = pd.read_csv(results_file)

print(f'✅ 加载了 {len(trades_df)} 笔交易')

# ============================================================================
# 分组
# ============================================================================

print('\n📊 分组分析...')

# 成功组：达到20%以上
winners = trades_df[trades_df['return'] >= 0.20].copy()

# 失败组：触发止损
losers = trades_df[trades_df['exit_reason'] == '止损-20%'].copy()

# 中间组：盈利但未达20%
mediocre = trades_df[
    (trades_df['return'] > 0) & 
    (trades_df['return'] < 0.20)
].copy()

print(f'成功组（达到20%）: {len(winners)} 笔 ({len(winners)/len(trades_df)*100:.1f}%)')
print(f'失败组（止损-20%）: {len(losers)} 笔 ({len(losers)/len(trades_df)*100:.1f}%)')
print(f'中间组（盈利<20%）: {len(mediocre)} 笔 ({len(mediocre)/len(trades_df)*100:.1f}%)')

# ============================================================================
# 重新提取详细特征
# ============================================================================

print('\n📊 提取详细特征（这需要一些时间）...')

db = DatabaseManager(is_verbose=False)
db.initialize()
loader = DataLoader(db)

def extract_detailed_features(trade_row, loader):
    """为每笔交易提取详细特征"""
    stock_id = trade_row['stock_id']
    buy_date = pd.to_datetime(trade_row['buy_date'])
    
    try:
        # 加载买入前的数据
        klines = loader.load_klines(
            stock_id=stock_id,
            term='daily',
            start_date=(buy_date - pd.Timedelta(days=300)).strftime('%Y%m%d'),
            end_date=buy_date.strftime('%Y%m%d'),
            adjust='qfq'
        )
        
        if len(klines) < 120:
            return None
        
        df = pd.DataFrame(klines)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date')
        
        # 买入那天
        buy_idx = df[df['date'] == buy_date].index
        if len(buy_idx) == 0:
            return None
        
        idx = buy_idx[0]
        
        features = {}
        
        # 1. 均线特征
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        ma_array = df.loc[idx, ['ma5', 'ma10', 'ma20', 'ma60']].values
        features['ma_std'] = np.std(ma_array) / df.loc[idx, 'close']
        
        # 2. 价格位置
        if idx >= 20:
            high_20 = df.loc[idx-20:idx, 'highest'].max()
            low_20 = df.loc[idx-20:idx, 'lowest'].min()
            if high_20 > low_20:
                features['position_20d'] = (df.loc[idx, 'close'] - low_20) / (high_20 - low_20)
        
        # 3. 跌幅（多周期）
        if idx >= 60:
            high_60 = df.loc[idx-60:idx, 'highest'].max()
            features['drawdown_60d'] = (high_60 - df.loc[idx, 'close']) / high_60
        
        if idx >= 120:
            high_120 = df.loc[idx-120:idx, 'highest'].max()
            features['drawdown_120d'] = (high_120 - df.loc[idx, 'close']) / high_120
        
        if idx >= 240:
            high_240 = df.loc[idx-240:idx, 'highest'].max()
            features['drawdown_240d'] = (high_240 - df.loc[idx, 'close']) / high_240
        
        # 4. 趋势
        if idx >= 20:
            features['return_5d'] = (df.loc[idx, 'close'] - df.loc[idx-5, 'close']) / df.loc[idx-5, 'close']
            features['return_10d'] = (df.loc[idx, 'close'] - df.loc[idx-10, 'close']) / df.loc[idx-10, 'close']
            features['return_20d'] = (df.loc[idx, 'close'] - df.loc[idx-20, 'close']) / df.loc[idx-20, 'close']
        
        # 5. 波动率
        if idx >= 20:
            returns = df.loc[idx-20:idx, 'close'].pct_change().dropna()
            features['volatility_20d'] = returns.std()
        
        if idx >= 60:
            returns_60 = df.loc[idx-60:idx, 'close'].pct_change().dropna()
            features['volatility_60d'] = returns_60.std()
        
        # 6. 成交量
        if idx >= 20:
            recent_vol = df.loc[idx-19:idx, 'volume'].values
            avg_vol = np.mean(recent_vol[:-1])
            current_vol = recent_vol[-1]
            features['volume_ratio'] = current_vol / avg_vol if avg_vol > 0 else 1
        
        # 7. 均线斜率
        if idx >= 20:
            ma60_now = df.loc[idx, 'ma60']
            ma60_20ago = df.loc[idx-20, 'ma60']
            features['ma60slope'] = (ma60_now - ma60_20ago) / ma60_20ago
        
        # 8. 震荡幅度
        if idx >= 20:
            high_20 = df.loc[idx-20:idx, 'highest'].max()
            low_20 = df.loc[idx-20:idx, 'lowest'].min()
            features['amplitude_20d'] = (high_20 - low_20) / df.loc[idx, 'close']
        
        # 9. 价格相对均线
        features['close_to_ma5'] = (df.loc[idx, 'close'] - df.loc[idx, 'ma5']) / df.loc[idx, 'ma5']
        features['close_to_ma20'] = (df.loc[idx, 'close'] - df.loc[idx, 'ma20']) / df.loc[idx, 'ma20']
        features['close_to_ma60'] = (df.loc[idx, 'close'] - df.loc[idx, 'ma60']) / df.loc[idx, 'ma60']
        
        return features
        
    except Exception as e:
        return None

# 抽样分析（各取200个避免太慢）
print('提取成功组特征（前200个）...')
winner_features = []
for idx, row in winners.head(200).iterrows():
    feats = extract_detailed_features(row, loader)
    if feats:
        feats['group'] = 'winner'
        feats['return'] = row['return']
        winner_features.append(feats)

print('提取失败组特征（前200个）...')
loser_features = []
for idx, row in losers.head(200).iterrows():
    feats = extract_detailed_features(row, loader)
    if feats:
        feats['group'] = 'loser'
        feats['return'] = row['return']
        loser_features.append(feats)

# 合并
all_features = winner_features + loser_features
features_df = pd.DataFrame(all_features)

print(f'\n✅ 提取了 {len(features_df)} 个样本')
print(f'   成功组: {len(winner_features)}')
print(f'   失败组: {len(loser_features)}')

# ============================================================================
# 对比分析
# ============================================================================

print('\n' + '='*80)
print('📊 成功组（达到20%）vs 失败组（止损）特征对比')
print('='*80)

# 按组统计
winner_stats = features_df[features_df['group']=='winner'].describe()
loser_stats = features_df[features_df['group']=='loser'].describe()

# 计算差异
comparison = pd.DataFrame({
    '失败组均值': loser_stats.loc['mean'],
    '成功组均值': winner_stats.loc['mean'],
})

comparison['绝对差异'] = comparison['成功组均值'] - comparison['失败组均值']
comparison['相对差异%'] = (comparison['成功组均值'] / comparison['失败组均值'] - 1) * 100

# 排除 return 和 group
comparison = comparison[~comparison.index.isin(['return', 'group'])]

# 按相对差异绝对值排序
comparison['abs_diff'] = abs(comparison['相对差异%'])
comparison = comparison.sort_values('abs_diff', ascending=False)

print(f'\nTop 15 差异最大的特征:')
print('-'*90)
print(f'{"特征":<25} {"失败组":<15} {"成功组":<15} {"相对差异%"}')
print('-'*90)

for feature in comparison.head(15).index:
    row = comparison.loc[feature]
    print(f'{feature:<25} {row["失败组均值"]:<15.4f} {row["成功组均值"]:<15.4f} {row["相对差异%"]:>10.1f}%')

# ============================================================================
# 关键特征识别
# ============================================================================

print('\n' + '='*80)
print('🔍 关键区分特征（差异>30%）')
print('='*80)

key_features = comparison[abs(comparison['相对差异%']) > 30].copy()

if len(key_features) > 0:
    print(f'\n发现 {len(key_features)} 个关键区分特征:')
    
    for i, (feature, row) in enumerate(key_features.iterrows(), 1):
        print(f'\n{i}. {feature}')
        print(f'   失败组: {row["失败组均值"]:.4f}')
        print(f'   成功组: {row["成功组均值"]:.4f}')
        print(f'   差异: {row["相对差异%"]:+.1f}%')
        
        # 给出具体建议
        if row['成功组均值'] > row['失败组均值']:
            # 成功组更大
            threshold = row['成功组均值'] * 0.8  # 取成功组均值的80%作为阈值
            print(f'   💡 建议: 增加过滤条件 {feature} >= {threshold:.4f}')
        else:
            # 成功组更小
            threshold = row['成功组均值'] * 1.2
            print(f'   💡 建议: 增加过滤条件 {feature} <= {threshold:.4f}')
else:
    print('\n⚠️ 没有发现差异特别大的特征（>30%）')
    print('说明两组在当前特征下很难区分，需要：')
    print('  1. 引入新的特征（技术形态、量价关系等）')
    print('  2. 或者用ML学习复杂的非线性组合')

# ============================================================================
# 可视化对比
# ============================================================================

print('\n📊 生成对比图表...')

# 选择最重要的几个特征绘图
top_features = comparison.head(10).index.tolist()

fig, axes = plt.subplots(3, 4, figsize=(20, 12))
axes = axes.flatten()

for idx, feature in enumerate(top_features):
    if idx >= len(axes):
        break
    
    ax = axes[idx]
    
    winner_data = features_df[features_df['group']=='winner'][feature].dropna()
    loser_data = features_df[features_df['group']=='loser'][feature].dropna()
    
    # 绘制分布
    ax.hist(loser_data, bins=20, alpha=0.5, label='止损组', color='red', edgecolor='black')
    ax.hist(winner_data, bins=20, alpha=0.5, label='达到20%组', color='green', edgecolor='black')
    
    # 标注均值
    ax.axvline(loser_data.mean(), color='red', linestyle='--', linewidth=2, label=f'止损均值')
    ax.axvline(winner_data.mean(), color='green', linestyle='--', linewidth=2, label=f'成功均值')
    
    ax.set_title(f'{feature}', fontsize=11, fontweight='bold')
    ax.set_xlabel('Value', fontsize=9)
    ax.set_ylabel('Frequency', fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

# 隐藏多余的子图
for idx in range(len(top_features), len(axes)):
    axes[idx].axis('off')

plt.tight_layout()
plot_file = os.path.join(os.path.dirname(__file__), '../requirements/winners_vs_losers.png')
plt.savefig(plot_file, dpi=150)
print(f'✅ 对比图表已保存: winners_vs_losers.png')
plt.close()

# ============================================================================
# 统计显著性测试（T检验）
# ============================================================================

print('\n' + '='*80)
print('📊 统计显著性检验（T检验）')
print('='*80)

from scipy import stats

print(f'\n检验两组是否有显著差异（p<0.05为显著）:')
print('-'*80)
print(f'{"特征":<25} {"T统计量":<15} {"P值":<15} {"显著性"}')
print('-'*80)

significant_features = []

for feature in comparison.head(15).index:
    winner_data = features_df[features_df['group']=='winner'][feature].dropna()
    loser_data = features_df[features_df['group']=='loser'][feature].dropna()
    
    if len(winner_data) > 0 and len(loser_data) > 0:
        t_stat, p_value = stats.ttest_ind(winner_data, loser_data)
        
        significance = ''
        if p_value < 0.001:
            significance = '*** 极显著'
            significant_features.append(feature)
        elif p_value < 0.01:
            significance = '** 很显著'
            significant_features.append(feature)
        elif p_value < 0.05:
            significance = '* 显著'
            significant_features.append(feature)
        else:
            significance = '不显著'
        
        print(f'{feature:<25} {t_stat:<15.4f} {p_value:<15.6f} {significance}')

# ============================================================================
# 基于显著特征的建议
# ============================================================================

print('\n' + '='*80)
print('💡 基于统计分析的优化建议')
print('='*80)

if len(significant_features) > 0:
    print(f'\n发现 {len(significant_features)} 个统计显著的区分特征:')
    
    suggestions = []
    
    for feature in significant_features[:5]:  # Top 5
        row = comparison.loc[feature]
        
        print(f'\n⭐ {feature}')
        print(f'   失败组: {row["失败组均值"]:.4f}')
        print(f'   成功组: {row["成功组均值"]:.4f}')
        print(f'   差异: {row["相对差异%"]:+.1f}%')
        
        # 建议阈值
        if row['成功组均值'] > row['失败组均值']:
            # 成功组更大，需要设下限
            suggested_threshold = row['成功组均值'] * 0.75
            suggestions.append(f'{feature} >= {suggested_threshold:.4f}')
            print(f'   💡 建议: {feature} >= {suggested_threshold:.4f}')
        else:
            # 成功组更小，需要设上限
            suggested_threshold = row['成功组均值'] * 1.25
            suggestions.append(f'{feature} <= {suggested_threshold:.4f}')
            print(f'   💡 建议: {feature} <= {suggested_threshold:.4f}')
    
    print(f'\n新的信号条件建议:')
    print('='*80)
    print('原有条件:')
    print('  - ma_std < 0.03')
    print('  - position < 0.30')
    print('  - -0.176 < ma60slope < 0.176')
    print('  - drawdown_120d >= 0.20')
    
    print('\n建议新增:')
    for i, sugg in enumerate(suggestions, 1):
        print(f'  {i}. {sugg}')

else:
    print('\n⚠️ 没有发现统计显著的差异')
    print('这意味着：')
    print('  1. 当前特征集无法有效区分成功/失败')
    print('  2. 需要引入全新的特征（如技术形态识别）')
    print('  3. 或者用ML学习更复杂的非线性规律')

# 保存详细特征
features_df.to_csv(os.path.join(os.path.dirname(__file__), '../requirements/winners_vs_losers_features.csv'), index=False)
print(f'\n✅ 详细特征已保存: winners_vs_losers_features.csv')

print('\n' + '='*80)
print('✅ 对比分析完成')
print('='*80)

