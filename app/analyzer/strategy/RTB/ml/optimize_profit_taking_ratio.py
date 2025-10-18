#!/usr/bin/env python3
"""
优化分段止盈比例
核心问题：如何分配仓位才能最大化数学期望值？
"""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader

print('='*80)
print('分段止盈比例优化 - 最大化数学期望值')
print('='*80)

# ============================================================================
# 加载数据
# ============================================================================

print('\n📊 加载数据...')

db = DatabaseManager(is_verbose=False)
db.initialize()
loader = DataLoader(db)
stock_list = loader.load_stock_list(filtered=True)
test_stocks = stock_list[:50]

# ============================================================================
# 当前V7信号条件
# ============================================================================

PARAMS = {
    'ma_std': 0.03,
    'position': 0.30,
    'ma60slope_min': 0.009,
    'ma60slope_max': 0.176,
    'drawdown_120d': 0.20,
    'return_20d_max': -0.07,
    'close_to_ma20_max': -0.05,
    'stop_loss': -0.20,
}

def calculate_features(df):
    """计算特征"""
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    ma_array = df[['ma5', 'ma10', 'ma20', 'ma60']].values
    df['ma_std'] = np.std(ma_array, axis=1) / df['close']
    
    high_20d = df['highest'].rolling(20).max()
    low_20d = df['lowest'].rolling(20).min()
    df['position'] = (df['close'] - low_20d) / (high_20d - low_20d)
    
    df['ma60_20d_ago'] = df['ma60'].shift(20)
    df['ma60slope'] = (df['ma60'] - df['ma60_20d_ago']) / df['ma60_20d_ago']
    
    high_120d = df['highest'].rolling(120).max()
    df['drawdown_120d'] = (high_120d - df['close']) / high_120d
    
    df['return_20d'] = df['close'].pct_change(20)
    df['close_to_ma20'] = (df['close'] - df['ma20']) / df['ma20']
    
    return df.dropna()

def find_signals(df):
    """V7信号"""
    return df[
        (df['ma_std'] < PARAMS['ma_std']) &
        (df['position'] < PARAMS['position']) &
        (df['drawdown_120d'] >= PARAMS['drawdown_120d']) &
        (df['ma60slope'] >= PARAMS['ma60slope_min']) &
        (df['ma60slope'] < PARAMS['ma60slope_max']) &
        (df['return_20d'] <= PARAMS['return_20d_max']) &
        (df['close_to_ma20'] <= PARAMS['close_to_ma20_max'])
    ]

def deduplicate(signals):
    """去重"""
    if len(signals) == 0:
        return signals
    signals = signals.sort_values(['stock_id', 'date']).reset_index(drop=True)
    deduped_indices = []
    last_buy = {}
    for idx, row in signals.iterrows():
        sid = row['stock_id']
        if sid in last_buy and (row['date'] - last_buy[sid]).days < 120:
            continue
        deduped_indices.append(idx)
        last_buy[sid] = row['date']
    return signals.loc[deduped_indices]

def simulate_with_ratio(stock_df, signal_idx, ratio_10, ratio_20, ratio_30, max_holding_days=120):
    """
    模拟交易，使用指定的分段止盈比例
    
    ratio_10: 10%档平仓比例
    ratio_20: 20%档平仓比例
    ratio_30: 30%档平仓比例（剩余仓位）
    
    返回: 总收益
    """
    buy_price = stock_df.iloc[signal_idx]['close']
    future_data = stock_df.iloc[signal_idx+1 : signal_idx+1+max_holding_days]
    
    if len(future_data) == 0:
        return None
    
    remaining_shares = 1.0
    total_return = 0.0
    
    sold_10 = False
    sold_20 = False
    
    for day_idx, (idx, day_data) in enumerate(future_data.iterrows(), 1):
        current_price = day_data['close']
        current_return = (current_price - buy_price) / buy_price
        
        # 止损 -20%
        if current_return <= PARAMS['stop_loss']:
            total_return += current_return * remaining_shares
            return total_return
        
        # 分段止盈
        if current_return >= 0.10 and not sold_10:
            total_return += current_return * ratio_10
            remaining_shares -= ratio_10
            sold_10 = True
        
        if current_return >= 0.20 and not sold_20:
            total_return += current_return * ratio_20
            remaining_shares -= ratio_20
            sold_20 = True
        
        if current_return >= 0.30 and remaining_shares > 0:
            total_return += current_return * remaining_shares
            return total_return
    
    # 到期
    final_price = future_data.iloc[-1]['close']
    final_return = (final_price - buy_price) / buy_price
    total_return += final_return * remaining_shares
    
    return total_return

# ============================================================================
# 提取信号
# ============================================================================

print('\n📊 提取V7信号...')

all_signals = []

for stock in test_stocks:
    try:
        klines = loader.load_klines(stock['id'], 'daily', '20100101', '', 'qfq')
        if len(klines) < 300:
            continue
        
        df = pd.DataFrame(klines)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        df['stock_id'] = stock['id']
        df['stock_name'] = stock['name']
        
        df = calculate_features(df)
        signals = find_signals(df)
        
        if len(signals) > 0:
            all_signals.append(signals)
    except:
        continue

all_signals_df = pd.concat(all_signals, ignore_index=True)
deduped = deduplicate(all_signals_df)

print(f'✅ 去重后信号数: {len(deduped)}')

# ============================================================================
# 测试不同的分段比例方案
# ============================================================================

print('\n' + '='*80)
print('📊 测试不同分段止盈比例方案')
print('='*80)

# 定义测试方案
test_plans = [
    {'name': 'V7当前 (30/30/40)', 'ratios': (0.30, 0.30, 0.40)},
    {'name': '均匀分配 (33/33/34)', 'ratios': (0.33, 0.33, 0.34)},
    {'name': '重仓20% (25/50/25)', 'ratios': (0.25, 0.50, 0.25)},
    {'name': '重仓20% (30/50/20)', 'ratios': (0.30, 0.50, 0.20)},
    {'name': '重仓20% (20/60/20)', 'ratios': (0.20, 0.60, 0.20)},
    {'name': '重仓20% (20/70/10)', 'ratios': (0.20, 0.70, 0.10)},
    {'name': '激进30% (20/20/60)', 'ratios': (0.20, 0.20, 0.60)},
    {'name': '保守10% (50/30/20)', 'ratios': (0.50, 0.30, 0.20)},
    {'name': '保守10% (60/30/10)', 'ratios': (0.60, 0.30, 0.10)},
    {'name': '全仓30% (0/0/100)', 'ratios': (0.00, 0.00, 1.00)},
    {'name': '两段式 (50/0/50)', 'ratios': (0.50, 0.00, 0.50)},
    {'name': '两段式 (0/50/50)', 'ratios': (0.00, 0.50, 0.50)},
]

print(f'\n测试 {len(test_plans)} 个方案...')

results = []

for plan in test_plans:
    name = plan['name']
    ratio_10, ratio_20, ratio_30 = plan['ratios']
    
    print(f'\n测试: {name}')
    print(f'  10%档: {ratio_10*100:.0f}%, 20%档: {ratio_20*100:.0f}%, 30%档: {ratio_30*100:.0f}%')
    
    trades = []
    
    for stock_id in deduped['stock_id'].unique():
        stock_signals = deduped[deduped['stock_id']==stock_id]
        
        try:
            klines = loader.load_klines(stock_id, 'daily', '20100101', '', 'qfq')
            df = pd.DataFrame(klines)
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date').reset_index(drop=True)
            
            for _, signal in stock_signals.iterrows():
                signal_idx = df[df['date'] == signal['date']].index
                if len(signal_idx) == 0:
                    continue
                
                ret = simulate_with_ratio(df, signal_idx[0], ratio_10, ratio_20, ratio_30)
                if ret is not None:
                    trades.append(ret)
        except:
            continue
    
    if len(trades) == 0:
        continue
    
    trades_arr = np.array(trades)
    
    avg_return = trades_arr.mean()
    median_return = np.median(trades_arr)
    win_rate = (trades_arr > 0).mean()
    loss_rate = (trades_arr < 0).mean()
    
    profitable = trades_arr[trades_arr > 0]
    losses = trades_arr[trades_arr < 0]
    
    avg_profit = profitable.mean() if len(profitable) > 0 else 0
    avg_loss = losses.mean() if len(losses) > 0 else 0
    
    # 计算期望值
    expected_value = avg_return
    
    # 达成率
    reach_10 = (trades_arr >= 0.10).mean()
    reach_20 = (trades_arr >= 0.20).mean()
    reach_30 = (trades_arr >= 0.30).mean()
    
    result = {
        'name': name,
        'ratio_10': ratio_10,
        'ratio_20': ratio_20,
        'ratio_30': ratio_30,
        'trades': len(trades),
        'avg_return': avg_return,
        'median_return': median_return,
        'expected_value': expected_value,
        'win_rate': win_rate,
        'loss_rate': loss_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'reach_10': reach_10,
        'reach_20': reach_20,
        'reach_30': reach_30,
    }
    
    results.append(result)
    
    print(f'  交易数: {len(trades)}')
    print(f'  期望值: {expected_value*100:.2f}%')
    print(f'  平均收益: {avg_return*100:.2f}%')
    print(f'  胜率: {win_rate*100:.1f}%')

# ============================================================================
# 结果对比
# ============================================================================

print('\n' + '='*80)
print('📊 方案对比（按期望值排序）')
print('='*80)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('expected_value', ascending=False)

print('\n' + '='*100)
print(f'{"方案":<25} {"10%":<6} {"20%":<6} {"30%":<6} {"期望值":<10} {"平均收益":<10} {"胜率":<8} {"20%达成"}')
print('='*100)

for _, row in results_df.iterrows():
    marker = ' ⭐' if row['name'] == 'V7当前 (30/30/40)' else ''
    marker = ' 👑' if row['expected_value'] == results_df['expected_value'].max() else marker
    
    print(f'{row["name"]:<25} '
          f'{row["ratio_10"]*100:>5.0f}% '
          f'{row["ratio_20"]*100:>5.0f}% '
          f'{row["ratio_30"]*100:>5.0f}% '
          f'{row["expected_value"]*100:>9.2f}% '
          f'{row["avg_return"]*100:>9.2f}% '
          f'{row["win_rate"]*100:>7.1f}% '
          f'{row["reach_20"]*100:>6.1f}%'
          f'{marker}')

# ============================================================================
# 最优方案分析
# ============================================================================

print('\n' + '='*80)
print('🏆 最优方案')
print('='*80)

best = results_df.iloc[0]
current = results_df[results_df['name'] == 'V7当前 (30/30/40)'].iloc[0]

print(f'\n最优方案: {best["name"]}')
print(f'  10%档: {best["ratio_10"]*100:.0f}%')
print(f'  20%档: {best["ratio_20"]*100:.0f}%')
print(f'  30%档: {best["ratio_30"]*100:.0f}%')
print(f'  期望值: {best["expected_value"]*100:.2f}%')
print(f'  平均收益: {best["avg_return"]*100:.2f}%')
print(f'  胜率: {best["win_rate"]*100:.1f}%')
print(f'  20%达成: {best["reach_20"]*100:.1f}%')

print(f'\nV7当前方案: {current["name"]}')
print(f'  期望值: {current["expected_value"]*100:.2f}%')
print(f'  平均收益: {current["avg_return"]*100:.2f}%')
print(f'  胜率: {current["win_rate"]*100:.1f}%')
print(f'  20%达成: {current["reach_20"]*100:.1f}%')

improvement = (best["expected_value"] / current["expected_value"] - 1) * 100

print(f'\n💡 改进幅度:')
print(f'  期望值提升: {improvement:+.1f}%')
print(f'  绝对提升: {(best["expected_value"] - current["expected_value"])*100:+.2f}个百分点')

if improvement > 5:
    print(f'\n  🎉 显著提升！建议采用最优方案')
elif improvement > 0:
    print(f'\n  ✅ 有小幅提升，可以考虑优化')
else:
    print(f'\n  ✅ 当前方案已接近最优')

# ============================================================================
# 详细分析
# ============================================================================

print('\n' + '='*80)
print('📊 期望值分解分析')
print('='*80)

print(f'\n为什么重仓20%可能更优？')
print(f'\n达成率数据:')
print(f'  10%达成率: {current["reach_10"]*100:.1f}%')
print(f'  20%达成率: {current["reach_20"]*100:.1f}%')
print(f'  30%达成率: {current["reach_30"]*100:.1f}%')

print(f'\n关键insight:')
print(f'  从10%→20%: 保持率 = {current["reach_20"]/current["reach_10"]*100:.1f}%')
print(f'  从20%→30%: 保持率 = {current["reach_30"]/current["reach_20"]*100:.1f}%')

print(f'\n解读:')
print(f'  ✅ 大部分能到10%的都能到20%')
print(f'  ❌ 但到20%后很难到30%（只有{current["reach_30"]/current["reach_20"]*100:.1f}%）')
print(f'\n  💡 所以在20%档多平仓是合理的！')

# 保存结果
output_file = os.path.join(os.path.dirname(__file__), '../requirements/PROFIT_TAKING_OPTIMIZATION.csv')
results_df.to_csv(output_file, index=False)

print(f'\n✅ 结果已保存: PROFIT_TAKING_OPTIMIZATION.csv')

print('\n' + '='*80)

