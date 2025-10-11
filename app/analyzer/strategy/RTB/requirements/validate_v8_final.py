#!/usr/bin/env python3
"""
RTB 策略 V8 最终验证 - 优化分段止盈比例
V8 = V7信号 + 优化止盈(0/50/50)
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
print('RTB 策略 V8 最终验证 - 优化分段止盈比例')
print('='*80)

# ============================================================================
# V8 参数
# ============================================================================

PARAMS_V8 = {
    # 信号条件（与V7相同）
    'ma_std': 0.03,
    'position': 0.30,
    'ma60slope_min': 0.009,
    'ma60slope_max': 0.176,
    'drawdown_120d': 0.20,
    'return_20d_max': -0.07,
    'close_to_ma20_max': -0.05,
    'stop_loss': -0.20,
    
    # 🆕 优化的分段止盈比例
    'ratio_10': 0.00,  # 10%档不平仓
    'ratio_20': 0.50,  # 20%档平50%
    'ratio_30': 0.50,  # 30%档平剩余50%
}

print('\n📋 V8 参数:')
print('  信号条件（与V7相同）:')
print(f'    ma_std < {PARAMS_V8["ma_std"]}')
print(f'    position < {PARAMS_V8["position"]}')
print(f'    drawdown_120d >= {PARAMS_V8["drawdown_120d"]}')
print(f'    ma60slope: {PARAMS_V8["ma60slope_min"]} ~ {PARAMS_V8["ma60slope_max"]}')
print(f'    return_20d <= {PARAMS_V8["return_20d_max"]}')
print(f'    close_to_ma20 <= {PARAMS_V8["close_to_ma20_max"]}')
print('  🆕 优化的分段止盈:')
print(f'    10%档: {PARAMS_V8["ratio_10"]*100:.0f}%（继续持有）')
print(f'    20%档: {PARAMS_V8["ratio_20"]*100:.0f}%（锁定一半）')
print(f'    30%档: {PARAMS_V8["ratio_30"]*100:.0f}%（全部止盈）')

# ============================================================================
# 特征计算
# ============================================================================

def calculate_features(df):
    """计算所有特征"""
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

def find_signals_v8(df):
    """V8版本信号条件（与V7相同）"""
    return df[
        (df['ma_std'] < PARAMS_V8['ma_std']) &
        (df['position'] < PARAMS_V8['position']) &
        (df['drawdown_120d'] >= PARAMS_V8['drawdown_120d']) &
        (df['ma60slope'] >= PARAMS_V8['ma60slope_min']) &
        (df['ma60slope'] < PARAMS_V8['ma60slope_max']) &
        (df['return_20d'] <= PARAMS_V8['return_20d_max']) &
        (df['close_to_ma20'] <= PARAMS_V8['close_to_ma20_max'])
    ]

def deduplicate(signals):
    """信号去重"""
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

def simulate_v8(stock_df, signal_idx, max_holding_days=120):
    """V8交易模拟（优化的分段止盈）"""
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
        if current_return <= PARAMS_V8['stop_loss']:
            return {
                'exit_reason': '止损-20%',
                'exit_day': day_idx,
                'return': current_return * remaining_shares + total_return
            }
        
        # 分段止盈
        if current_return >= 0.10 and not sold_10:
            total_return += current_return * PARAMS_V8['ratio_10']
            remaining_shares -= PARAMS_V8['ratio_10']
            sold_10 = True
        
        if current_return >= 0.20 and not sold_20:
            total_return += current_return * PARAMS_V8['ratio_20']
            remaining_shares -= PARAMS_V8['ratio_20']
            sold_20 = True
        
        if current_return >= 0.30 and remaining_shares > 0:
            total_return += current_return * remaining_shares
            return {
                'exit_reason': '止盈30%',
                'exit_day': day_idx,
                'return': total_return
            }
    
    # 到期
    final_price = future_data.iloc[-1]['close']
    final_return = (final_price - buy_price) / buy_price
    
    return {
        'exit_reason': '到期120天',
        'exit_day': len(future_data),
        'return': final_return * remaining_shares + total_return
    }

# ============================================================================
# 加载数据
# ============================================================================

print('\n📊 加载数据...')

db = DatabaseManager(is_verbose=False)
db.initialize()

loader = DataLoader(db)
stock_list = loader.load_stock_list()

test_stocks = stock_list[:50]
print(f'✅ 测试 {len(test_stocks)} 只股票')

# ============================================================================
# 提取V8信号
# ============================================================================

print('\n📊 提取V8信号...')

all_signals = []
stocks_processed = 0

for i, stock in enumerate(test_stocks):
    stock_id = stock['id']
    stock_name = stock['name']
    
    try:
        klines = loader.load_klines(
            stock_id=stock_id,
            term='daily',
            start_date='20100101',
            end_date='',
            adjust='qfq'
        )
        
        if len(klines) < 300:
            continue
        
        df = pd.DataFrame(klines)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        df['stock_id'] = stock_id
        df['stock_name'] = stock_name
        
        df = calculate_features(df)
        signals = find_signals_v8(df)
        
        if len(signals) > 0:
            all_signals.append(signals)
            stocks_processed += 1
        
    except Exception as e:
        continue

if len(all_signals) == 0:
    print('\n❌ 没有找到任何信号')
    sys.exit(1)

all_signals_df = pd.concat(all_signals, ignore_index=True)

print(f'\n去重前: {len(all_signals_df)} 个信号')

deduped = deduplicate(all_signals_df)

print(f'去重后: {len(deduped)} 个信号')

# ============================================================================
# 模拟交易
# ============================================================================

print('\n📊 模拟V8交易（优化止盈）...')

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
            
            trade = simulate_v8(df, signal_idx[0])
            if trade:
                trade.update({
                    'stock_id': stock_id,
                    'stock_name': stock_signals.iloc[0]['stock_name'],
                    'buy_date': signal['date'],
                })
                trades.append(trade)
    except:
        continue

trades_v8 = pd.DataFrame(trades)

print(f'✅ 模拟了 {len(trades_v8)} 笔交易')

# ============================================================================
# 结果分析
# ============================================================================

print('\n' + '='*80)
print('📈 V8 优化版本 - 真实交易表现')
print('='*80)

# 退出原因
exit_reasons = trades_v8['exit_reason'].value_counts()
print('\n退出原因分布:')
for reason, count in exit_reasons.items():
    pct = count / len(trades_v8) * 100
    print(f'  {reason}: {count} 笔 ({pct:.1f}%)')

# 收益统计
print('\n收益率统计:')
print(f'  平均收益: {trades_v8["return"].mean()*100:.2f}%')
print(f'  中位数:   {trades_v8["return"].median()*100:.2f}%')
print(f'  最大收益: {trades_v8["return"].max()*100:.2f}%')
print(f'  最小收益: {trades_v8["return"].min()*100:.2f}%')

# 盈亏
profitable = trades_v8[trades_v8['return'] > 0]
loss = trades_v8[trades_v8['return'] < 0]

print(f'\n盈亏分布:')
print(f'  盈利: {len(profitable)} 笔 ({len(profitable)/len(trades_v8)*100:.1f}%)')
print(f'  亏损: {len(loss)} 笔 ({len(loss)/len(trades_v8)*100:.1f}%)')

if len(loss) > 0:
    print(f'  平均亏损: {loss["return"].mean()*100:.2f}%')

# 目标达成
print(f'\n分段目标达成:')
for target in [0.10, 0.15, 0.20, 0.25, 0.30]:
    count = len(trades_v8[trades_v8['return'] >= target])
    rate = count / len(trades_v8) * 100
    marker = ''
    if target == 0.20:
        marker = ' 🎯 主目标'
    elif target == 0.30:
        marker = ' ⭐ 次级目标'
    print(f'  {int(target*100):>3}%: {count:>4} 笔 ({rate:>5.1f}%){marker}')

# ============================================================================
# 版本对比
# ============================================================================

print('\n' + '='*80)
print('📊 版本演进对比')
print('='*80)

print(f'\n{"版本":<35} {"信号数":<10} {"期望值":<10} {"盈利率":<10} {"止损率":<10} {"20%达成":<10} {"30%达成"}')
print('-'*105)

# V7结果（从之前的运行）
v7_data = pd.read_csv('/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/requirements/V7_RESULTS.csv')
v7_stats = {
    'signals': len(v7_data),
    'expected': v7_data['return'].mean() * 100,
    'win_rate': (v7_data['return'] > 0).mean() * 100,
    'stop_rate': (v7_data['exit_reason'] == '止损-20%').sum() / len(v7_data) * 100,
    'reach_20': (v7_data['return'] >= 0.20).mean() * 100,
    'reach_30': (v7_data['return'] >= 0.30).mean() * 100,
}

# V8当前结果
v8_stats = {
    'signals': len(trades_v8),
    'expected': trades_v8['return'].mean() * 100,
    'win_rate': len(profitable) / len(trades_v8) * 100,
    'stop_rate': exit_reasons.get('止损-20%', 0) / len(trades_v8) * 100,
    'reach_20': (trades_v8['return'] >= 0.20).mean() * 100,
    'reach_30': (trades_v8['return'] >= 0.30).mean() * 100,
}

print(f'{"V7: 信号优化 + 止盈(30/30/40)":<35} '
      f'{v7_stats["signals"]:<10} '
      f'{v7_stats["expected"]:<9.2f}% '
      f'{v7_stats["win_rate"]:<9.1f}% '
      f'{v7_stats["stop_rate"]:<9.1f}% '
      f'{v7_stats["reach_20"]:<9.1f}% '
      f'{v7_stats["reach_30"]:.1f}%')

print(f'{"V8: 信号优化 + 止盈(0/50/50) 🆕":<35} '
      f'{v8_stats["signals"]:<10} '
      f'{v8_stats["expected"]:<9.2f}% '
      f'{v8_stats["win_rate"]:<9.1f}% '
      f'{v8_stats["stop_rate"]:<9.1f}% '
      f'{v8_stats["reach_20"]:<9.1f}% '
      f'{v8_stats["reach_30"]:.1f}%')

# ============================================================================
# 改进分析
# ============================================================================

print('\n改进效果（V8 vs V7）:')

improvement_expected = (v8_stats['expected'] / v7_stats['expected'] - 1) * 100
improvement_reach20 = v8_stats['reach_20'] - v7_stats['reach_20']
improvement_stop = v7_stats['stop_rate'] - v8_stats['stop_rate']

if v8_stats['expected'] > v7_stats['expected']:
    print(f'  ✅ 期望值提升: {improvement_expected:+.1f}%')
else:
    print(f'  ❌ 期望值下降: {improvement_expected:+.1f}%')

if v8_stats['stop_rate'] < v7_stats['stop_rate']:
    print(f'  ✅ 止损率降低: {improvement_stop:+.1f}个百分点')
else:
    print(f'  ⚠️ 止损率上升: {-improvement_stop:+.1f}个百分点')

if v8_stats['reach_20'] > v7_stats['reach_20']:
    print(f'  ✅ 20%达成率提升: {improvement_reach20:+.1f}个百分点')
else:
    print(f'  ⚠️ 20%达成率下降: {improvement_reach20:+.1f}个百分点')

# ============================================================================
# 数学期望值分析
# ============================================================================

print('\n' + '='*80)
print('📊 数学期望值分析')
print('='*80)

# V7期望值
v7_盈利率 = v7_stats['win_rate'] / 100
v7_盈利 = v7_data[v7_data['return'] > 0]['return'].mean()
v7_亏损率 = 1 - v7_盈利率
v7_亏损 = v7_data[v7_data['return'] < 0]['return'].mean()
v7_期望值 = v7_盈利率 * v7_盈利 + v7_亏损率 * v7_亏损

print(f'\nV7期望值计算:')
print(f'  {v7_盈利率:.4f} × {v7_盈利:.4f} + {v7_亏损率:.4f} × {v7_亏损:.4f}')
print(f'  = {v7_期望值:.6f} ({v7_期望值*100:.2f}%)')

# V8期望值
v8_盈利率 = v8_stats['win_rate'] / 100
v8_盈利 = profitable['return'].mean()
v8_亏损率 = 1 - v8_盈利率
v8_亏损 = loss['return'].mean()
v8_期望值 = v8_盈利率 * v8_盈利 + v8_亏损率 * v8_亏损

print(f'\nV8期望值计算:')
print(f'  {v8_盈利率:.4f} × {v8_盈利:.4f} + {v8_亏损率:.4f} × {v8_亏损:.4f}')
print(f'  = {v8_期望值:.6f} ({v8_期望值*100:.2f}%)')

期望值提升 = (v8_期望值 / v7_期望值 - 1) * 100

print(f'\n期望值提升: {期望值提升:+.1f}%')

# 考虑交易成本
交易成本 = 0.003
v7_净期望值 = v7_期望值 - 交易成本
v8_净期望值 = v8_期望值 - 交易成本

print(f'\n扣除交易成本（0.3%）:')
print(f'  V7净期望值: {v7_净期望值*100:.2f}%')
print(f'  V8净期望值: {v8_净期望值*100:.2f}%')

# 凯利准则
v8_盈亏比 = abs(v8_盈利 / v8_亏损)
v8_凯利 = (v8_盈利率 * v8_盈亏比 - v8_亏损率) / v8_盈亏比

print(f'\nV8凯利建议仓位:')
print(f'  盈亏比: {v8_盈亏比:.2f}')
print(f'  凯利值: {v8_凯利*100:.1f}%')

# ============================================================================
# 结论
# ============================================================================

print('\n' + '='*80)
print('✅ V8 最终结论')
print('='*80)

print(f'\n核心指标对比:')
print(f'  期望值: {v7_stats["expected"]:.2f}% → {v8_stats["expected"]:.2f}% ({improvement_expected:+.1f}%)')
print(f'  盈利率: {v7_stats["win_rate"]:.1f}% → {v8_stats["win_rate"]:.1f}%')
print(f'  止损率: {v7_stats["stop_rate"]:.1f}% → {v8_stats["stop_rate"]:.1f}%')
print(f'  20%达成率: {v7_stats["reach_20"]:.1f}% → {v8_stats["reach_20"]:.1f}% ({improvement_reach20:+.1f}pp)')

print('\n评价:')

if improvement_expected > 5:
    print('  🎉 V8显著优于V7！建议采用V8')
    print('  ✅ 优化的分段止盈比例(0/50/50)明显提升期望值')
elif improvement_expected > 0:
    print('  ✅ V8小幅优于V7，建议采用V8')
    print('  优化的分段止盈比例有改进')
else:
    print('  ⚠️ V8未能提升表现')
    print('  建议继续使用V7')

# 保存结果
output_file = os.path.join(os.path.dirname(__file__), 'V8_FINAL_RESULTS.csv')
trades_v8.to_csv(output_file, index=False)
print(f'\n✅ V8结果已保存: V8_FINAL_RESULTS.csv')

print('\n' + '='*80)
print('RTB策略最终版本确定')
print('='*80)

if improvement_expected > 0:
    print('\n🏆 最终推荐: V8')
    print('  信号条件:')
    print('    - ma_std < 0.03')
    print('    - position < 0.30')
    print('    - drawdown_120d >= 0.20')
    print('    - ma60slope: 0.009 ~ 0.176')
    print('    - return_20d <= -0.07')
    print('    - close_to_ma20 <= -0.05')
    print('  分段止盈:')
    print('    - 10%档: 0% （继续持有）')
    print('    - 20%档: 50%（锁定一半）')
    print('    - 30%档: 50%（全部止盈）')
    print('  止损: -20%')
    print(f'  期望值: {v8_stats["expected"]:.2f}%')
    print(f'  凯利仓位: {v8_凯利*100:.1f}%')
else:
    print('\n🏆 最终推荐: V7')
    print('  （V8未能改进，保持V7配置）')

print('\n' + '='*80)

