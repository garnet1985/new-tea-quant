#!/usr/bin/env python3
"""
RTB 策略验证 V5 - 信号去重版本
修正：同一只股票连续满足条件的只算一个信号
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
print('RTB 策略验证 V5 - 信号去重版（正确版本）')
print('='*80)

# ============================================================================
# 特征计算
# ============================================================================

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
    
    return df.dropna()

def find_signals(df):
    """找出原始信号"""
    signals = df[
        (df['ma_std'] < 0.03) &
        (df['position'] < 0.30) &
        (df['ma60slope'] > -0.176) &
        (df['ma60slope'] < 0.176)
    ].copy()
    
    return signals

def deduplicate_signals(signals, cooling_period=120):
    """
    信号去重：同一只股票连续满足条件的只保留第一个
    
    Args:
        signals: 原始信号DataFrame
        cooling_period: 冷却期（天），买入后N天内不再买同一只股票
    
    Returns:
        去重后的信号
    """
    if len(signals) == 0:
        return signals
    
    # 按股票和日期排序
    signals = signals.sort_values(['stock_id', 'date']).reset_index(drop=True)
    
    # 去重逻辑
    deduped_indices = []
    last_buy_date = {}  # 记录每只股票上次买入日期
    
    for idx, row in signals.iterrows():
        stock_id = row['stock_id']
        current_date = row['date']
        
        # 检查冷却期
        if stock_id in last_buy_date:
            days_since_last_buy = (current_date - last_buy_date[stock_id]).days
            
            if days_since_last_buy < cooling_period:
                # 还在冷却期，跳过
                continue
        
        # 这是一个新信号
        deduped_indices.append(idx)
        last_buy_date[stock_id] = current_date
    
    deduped = signals.loc[deduped_indices].reset_index(drop=True)
    
    return deduped

# ============================================================================
# 真实交易模拟
# ============================================================================

def simulate_real_trade(stock_df, signal_idx, max_holding_days=120):
    """模拟真实交易（含止损止盈）"""
    buy_price = stock_df.iloc[signal_idx]['close']
    
    future_data = stock_df.iloc[signal_idx+1 : signal_idx+1+max_holding_days]
    
    if len(future_data) == 0:
        return None
    
    remaining_shares = 1.0
    total_return = 0.0
    break_even_activated = False
    max_return_seen = 0.0
    
    for day_idx, (idx, day_data) in enumerate(future_data.iterrows(), 1):
        current_price = day_data['close']
        current_return = (current_price - buy_price) / buy_price
        
        if current_return > max_return_seen:
            max_return_seen = current_return
        
        # 止损 -15%
        if current_return <= -0.15:
            return {
                'exit_reason': '止损-15%',
                'exit_day': day_idx,
                'exit_price': current_price,
                'return': current_return * remaining_shares + total_return,
                'max_return_seen': max_return_seen,
            }
        
        # 保本止损
        if break_even_activated and current_return <= 0:
            return {
                'exit_reason': '保本止损',
                'exit_day': day_idx,
                'exit_price': current_price,
                'return': current_return * remaining_shares + total_return,
                'max_return_seen': max_return_seen,
            }
        
        # 分段止盈
        if current_return >= 0.10 and remaining_shares == 1.0:
            sell_ratio = 0.30
            total_return += current_return * sell_ratio
            remaining_shares -= sell_ratio
            break_even_activated = True
        elif current_return >= 0.20 and remaining_shares == 0.70:
            sell_ratio = 0.30
            total_return += current_return * sell_ratio
            remaining_shares -= sell_ratio
        elif current_return >= 0.30 and remaining_shares > 0:
            total_return += current_return * remaining_shares
            return {
                'exit_reason': '止盈30%',
                'exit_day': day_idx,
                'exit_price': current_price,
                'return': total_return,
                'max_return_seen': max_return_seen,
            }
    
    # 到期
    final_price = future_data.iloc[-1]['close']
    final_return = (final_price - buy_price) / buy_price
    
    return {
        'exit_reason': '到期120天',
        'exit_day': len(future_data),
        'exit_price': final_price,
        'return': final_return * remaining_shares + total_return,
        'max_return_seen': max_return_seen,
    }

# ============================================================================
# 主流程
# ============================================================================

print('\n📊 加载数据...')
db = DatabaseManager(is_verbose=False)
db.initialize()

loader = DataLoader(db)
stock_list = loader.load_stock_list()

test_stocks = stock_list[:20]
print(f'✅ 测试 {len(test_stocks)} 只股票')

print('\n📊 提取信号（去重前）...')

all_signals_before_dedup = []
stocks_processed = 0

for i, stock in enumerate(test_stocks):
    stock_id = stock['id']
    stock_name = stock['name']
    
    try:
        klines = loader.load_klines(
            stock_id=stock_id,
            term='daily',
            start_date='20150101',
            end_date='',
            adjust='qfq'
        )
        
        if len(klines) < 200:
            continue
            
        df = pd.DataFrame(klines)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        df['stock_id'] = stock_id
        df['stock_name'] = stock_name
        
        df = calculate_features(df)
        signals = find_signals(df)
        
        if len(signals) > 0:
            all_signals_before_dedup.append(signals)
            stocks_processed += 1
            print(f'  [{stocks_processed}] {stock_name}: {len(signals)} 个信号（去重前）')
        
    except Exception as e:
        print(f'  ⚠️ 跳过 {stock_name}: {e}')
        continue

if len(all_signals_before_dedup) == 0:
    print('❌ 没有找到任何信号')
    sys.exit(1)

# 合并
all_signals = pd.concat(all_signals_before_dedup, ignore_index=True)
print(f'\n去重前总信号数: {len(all_signals)}')

# ============================================================================
# 去重！
# ============================================================================

print('\n📊 信号去重（冷却期120天）...')

deduped_signals = deduplicate_signals(all_signals, cooling_period=120)

print(f'✅ 去重后信号数: {len(deduped_signals)}')
print(f'   去除了: {len(all_signals) - len(deduped_signals)} 个重复信号')
print(f'   去重比例: {(1 - len(deduped_signals)/len(all_signals))*100:.1f}%')

# ============================================================================
# 模拟交易（只用去重后的信号）
# ============================================================================

print('\n📊 模拟真实交易（去重后的信号）...')

all_trades = []

# 需要重新加载数据来模拟
for stock_id in deduped_signals['stock_id'].unique():
    stock_name = deduped_signals[deduped_signals['stock_id']==stock_id].iloc[0]['stock_name']
    stock_signals = deduped_signals[deduped_signals['stock_id']==stock_id]
    
    try:
        # 加载完整数据
        klines = loader.load_klines(
            stock_id=stock_id,
            term='daily',
            start_date='20150101',
            end_date='',
            adjust='qfq'
        )
        
        df = pd.DataFrame(klines)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        
        # 对每个去重后的信号模拟
        for _, signal_row in stock_signals.iterrows():
            signal_date = signal_row['date']
            
            # 找到对应的索引
            signal_idx = df[df['date'] == signal_date].index
            if len(signal_idx) == 0:
                continue
            
            signal_idx = signal_idx[0]
            
            # 模拟交易
            trade_result = simulate_real_trade(df, signal_idx, max_holding_days=120)
            
            if trade_result:
                trade_result.update({
                    'stock_id': stock_id,
                    'stock_name': stock_name,
                    'buy_date': signal_date,
                    'buy_price': df.iloc[signal_idx]['close'],
                })
                all_trades.append(trade_result)
        
    except Exception as e:
        continue

print(f'\n✅ 模拟了 {len(all_trades)} 笔交易（去重后）')

if len(all_trades) == 0:
    print('❌ 没有成功模拟任何交易')
    sys.exit(1)

# ============================================================================
# 分析结果
# ============================================================================

trades_v5 = pd.DataFrame(all_trades)

print('\n' + '='*80)
print('📈 V5 去重版本 - 真实模拟结果')
print('='*80)

# 退出原因
print('\n退出原因分布:')
exit_reasons = trades_v5['exit_reason'].value_counts()
for reason, count in exit_reasons.items():
    pct = count / len(trades_v5) * 100
    print(f'  {reason}: {count} 笔 ({pct:.1f}%)')

# 收益统计
print('\n收益率统计:')
print(f'  平均收益: {trades_v5["return"].mean()*100:.2f}%')
print(f'  中位数:   {trades_v5["return"].median()*100:.2f}%')
print(f'  最大收益: {trades_v5["return"].max()*100:.2f}%')
print(f'  最小收益: {trades_v5["return"].min()*100:.2f}%')

# 盈亏
profitable = trades_v5[trades_v5['return'] > 0]
loss = trades_v5[trades_v5['return'] < 0]

print(f'\n盈亏分布:')
print(f'  盈利: {len(profitable)} 笔 ({len(profitable)/len(trades_v5)*100:.1f}%)')
print(f'  亏损: {len(loss)} 笔 ({len(loss)/len(trades_v5)*100:.1f}%)')

if len(loss) > 0:
    print(f'  平均亏损: {loss["return"].mean()*100:.2f}%')

# 目标达成
达到10 = len(trades_v5[trades_v5['return'] >= 0.10])
达到20 = len(trades_v5[trades_v5['return'] >= 0.20])
达到30 = len(trades_v5[trades_v5['return'] >= 0.30])

print(f'\n分段目标达成:')
print(f'  10%: {达到10} 笔 ({达到10/len(trades_v5)*100:.1f}%)')
print(f'  20%: {达到20} 笔 ({达到20/len(trades_v5)*100:.1f}%)')
print(f'  30%: {达到30} 笔 ({达到30/len(trades_v5)*100:.1f}%)')

# ============================================================================
# V3 vs V5 对比
# ============================================================================

print('\n' + '='*80)
print('📊 V3（未去重）vs V5（去重）对比')
print('='*80)

print('\n【V3 版本 - 未去重（错误版本）】')
print(f'  信号数量: 12,457 个 ❌ 虚高！')
print(f'  平均收益: 0.69%')
print(f'  盈利率:   53.7%')
print(f'  止损率:   37.0%')
print(f'  30%达成:  1.5%')

print(f'\n【V5 版本 - 去重后（正确版本）】')
print(f'  信号数量: {len(trades_v5)} 个 ✅ 真实数量')
print(f'  平均收益: {trades_v5["return"].mean()*100:.2f}%')
print(f'  盈利率:   {len(profitable)/len(trades_v5)*100:.1f}%')

止损count = exit_reasons.get('止损-15%', 0)
print(f'  止损率:   {止损count/len(trades_v5)*100:.1f}%')
print(f'  30%达成:  {达到30/len(trades_v5)*100:.1f}%')

print(f'\n对比分析:')
print(f'  信号减少: {(1 - len(trades_v5)/12457)*100:.1f}%')

if trades_v5["return"].mean() > 0.0069:
    print(f'  ✅ 平均收益提升: {(trades_v5["return"].mean()/0.0069 - 1)*100:.1f}%')
else:
    print(f'  ❌ 平均收益下降: {(1 - trades_v5["return"].mean()/0.0069)*100:.1f}%')

if len(profitable)/len(trades_v5) > 0.537:
    print(f'  ✅ 盈利率提升: {(len(profitable)/len(trades_v5) - 0.537)*100:.1f}个百分点')
else:
    print(f'  ❌ 盈利率下降: {(0.537 - len(profitable)/len(trades_v5))*100:.1f}个百分点')

# 保存
output_file = '/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/requirements/deduped_trade_results.csv'
trades_v5.to_csv(output_file, index=False)

print('\n' + '='*80)
print('✅ V5 验证完成（正确版本）')
print('='*80)

print(f'\n核心指标:')
print(f'  真实信号数: {len(trades_v5)}')
print(f'  盈利率: {len(profitable)/len(trades_v5)*100:.1f}%')
print(f'  平均收益: {trades_v5["return"].mean()*100:.2f}%')
print(f'  30%达成率: {达到30/len(trades_v5)*100:.1f}%')

print(f'\n✅ 详细结果已保存: {output_file}')

# ============================================================================
# 结论
# ============================================================================

print('\n' + '='*80)
print('💡 真实策略表现（去重后）')
print('='*80)

if 达到30/len(trades_v5) > 0.20:
    print('\n🎉 策略表现优秀！')
    print(f'  30%达成率超过20%，可以直接使用或用ML锦上添花')
elif 达到30/len(trades_v5) > 0.10:
    print('\n✅ 策略表现良好！')
    print(f'  30%达成率在10-20%之间，建议用ML优化')
elif 达到30/len(trades_v5) > 0.05:
    print('\n⚠️ 策略表现一般')
    print(f'  30%达成率在5-10%之间，需要ML优化或调整策略')
else:
    print('\n❌ 策略表现不佳')
    print(f'  30%达成率<5%，建议：')
    print(f'    1. 重新设计特征')
    print(f'    2. 降低目标（20%可能更合理）')
    print(f'    3. 或者这个策略思路可能不适合')

print('\n' + '='*80)

