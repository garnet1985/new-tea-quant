#!/usr/bin/env python3
"""
RTB 策略最终验证 - 使用ML优化后的参数
- drawdown_120d >= 0.20（半年至少跌20%）
- 止损：-20%（不是-15%）
- 无保本止损（取消）
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
print('RTB 策略最终验证 - ML优化后的参数')
print('='*80)

# ============================================================================
# 最优参数
# ============================================================================

PARAMS = {
    'ma_std': 0.03,
    'position': 0.30,
    'ma60slope_min': -0.176,
    'ma60slope_max': 0.176,
    'drawdown_120d': 0.20,  # 🆕 ML发现的关键参数
    'stop_loss': -0.20,      # 🆕 优化后的止损
    'break_even': False,     # 🆕 取消保本止损
}

print('\n📋 使用参数:')
for key, value in PARAMS.items():
    print(f'  {key}: {value}')

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
    
    # 🆕 120天跌幅（ML发现的最重要特征）
    high_120d = df['highest'].rolling(120).max()
    df['drawdown_120d'] = (high_120d - df['close']) / high_120d
    
    return df.dropna()

def find_signals(df):
    """使用最优参数找信号"""
    return df[
        (df['ma_std'] < PARAMS['ma_std']) &
        (df['position'] < PARAMS['position']) &
        (df['ma60slope'] > PARAMS['ma60slope_min']) &
        (df['ma60slope'] < PARAMS['ma60slope_max']) &
        (df['drawdown_120d'] >= PARAMS['drawdown_120d'])
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

def simulate_real_trade(stock_df, signal_idx, max_holding_days=120):
    """真实交易模拟（使用最优参数）"""
    buy_price = stock_df.iloc[signal_idx]['close']
    future_data = stock_df.iloc[signal_idx+1 : signal_idx+1+max_holding_days]
    
    if len(future_data) == 0:
        return None
    
    remaining_shares = 1.0
    total_return = 0.0
    
    for day_idx, (idx, day_data) in enumerate(future_data.iterrows(), 1):
        current_price = day_data['close']
        current_return = (current_price - buy_price) / buy_price
        
        # 固定止损 -20%
        if current_return <= PARAMS['stop_loss']:
            return {
                'exit_reason': '止损-20%',
                'exit_day': day_idx,
                'return': current_return * remaining_shares + total_return
            }
        
        # 🆕 无保本止损！
        
        # 分段止盈
        if current_return >= 0.10 and remaining_shares == 1.0:
            total_return += current_return * 0.30
            remaining_shares = 0.70
        elif current_return >= 0.20 and remaining_shares == 0.70:
            total_return += current_return * 0.30
            remaining_shares = 0.40
        elif current_return >= 0.30 and remaining_shares > 0:
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

print('\n📊 加载股票数据...')

db = DatabaseManager(is_verbose=False)
db.initialize()

loader = DataLoader(db)
stock_list = loader.load_stock_list()

# 测试50只股票
TEST_SIZE = 50
test_stocks = stock_list[:TEST_SIZE]

print(f'✅ 将测试 {TEST_SIZE} 只股票')

# ============================================================================
# 提取信号
# ============================================================================

print('\n📊 提取信号...')

all_signals = []
stocks_processed = 0

for i, stock in enumerate(test_stocks):
    stock_id = stock['id']
    stock_name = stock['name']
    
    try:
        klines = loader.load_klines(
            stock_id=stock_id,
            term='daily',
            start_date='20100101',  # 更早数据以计算120天跌幅
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
        signals = find_signals(df)
        
        if len(signals) > 0:
            all_signals.append(signals)
            stocks_processed += 1
            print(f'  [{stocks_processed}] {stock_name}: {len(signals)} 个信号')
        
    except Exception as e:
        continue

if len(all_signals) == 0:
    print('❌ 没有找到任何信号')
    sys.exit(1)

all_signals_df = pd.concat(all_signals, ignore_index=True)

print(f'\n去重前: {len(all_signals_df)} 个信号')

deduped = deduplicate(all_signals_df)

print(f'去重后: {len(deduped)} 个信号')
print(f'去重比例: {(1 - len(deduped)/len(all_signals_df))*100:.1f}%')

# ============================================================================
# 模拟交易
# ============================================================================

print('\n📊 模拟真实交易...')

all_trades = []

for stock_id in deduped['stock_id'].unique():
    stock_signals = deduped[deduped['stock_id']==stock_id]
    stock_name = stock_signals.iloc[0]['stock_name']
    
    try:
        klines = loader.load_klines(stock_id, 'daily', '20100101', '', 'qfq')
        
        df = pd.DataFrame(klines)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        
        for _, signal in stock_signals.iterrows():
            signal_idx = df[df['date'] == signal['date']].index
            if len(signal_idx) == 0:
                continue
            
            trade = simulate_real_trade(df, signal_idx[0])
            if trade:
                trade.update({
                    'stock_id': stock_id,
                    'stock_name': stock_name,
                    'buy_date': signal['date'],
                    'buy_price': df.iloc[signal_idx[0]]['close'],
                    'drawdown_120d': signal['drawdown_120d'],
                })
                all_trades.append(trade)
        
    except Exception as e:
        continue

trades_df = pd.DataFrame(all_trades)

print(f'✅ 模拟了 {len(trades_df)} 笔交易')

# ============================================================================
# 结果分析
# ============================================================================

print('\n' + '='*80)
print('📈 最终优化版本 - 真实交易表现')
print('='*80)

# 退出原因
print('\n退出原因分布:')
exit_reasons = trades_df['exit_reason'].value_counts()
for reason, count in exit_reasons.items():
    pct = count / len(trades_df) * 100
    print(f'  {reason}: {count} 笔 ({pct:.1f}%)')

# 收益统计
print('\n收益率统计:')
print(f'  平均收益: {trades_df["return"].mean()*100:.2f}%')
print(f'  中位数:   {trades_df["return"].median()*100:.2f}%')
print(f'  最大收益: {trades_df["return"].max()*100:.2f}%')
print(f'  最小收益: {trades_df["return"].min()*100:.2f}%')

# 盈亏
profitable = trades_df[trades_df['return'] > 0]
loss = trades_df[trades_df['return'] < 0]

print(f'\n盈亏分布:')
print(f'  盈利: {len(profitable)} 笔 ({len(profitable)/len(trades_df)*100:.1f}%)')
print(f'  亏损: {len(loss)} 笔 ({len(loss)/len(trades_df)*100:.1f}%)')

if len(loss) > 0:
    print(f'  平均亏损: {loss["return"].mean()*100:.2f}%')
    print(f'  最大亏损: {loss["return"].min()*100:.2f}%')

# 目标达成
print(f'\n分段目标达成（真实交易收益）:')
for target in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
    count = len(trades_df[trades_df['return'] >= target])
    rate = count / len(trades_df) * 100
    marker = ''
    if target == 0.30:
        marker = ' ⭐ 核心目标'
    elif target == 0.20:
        marker = ' 🎯 次级目标'
    print(f'  {int(target*100):>3}%: {count:>4} 笔 ({rate:>5.1f}%){marker}')

# 特征统计
print(f'\n信号特征统计:')
print(f'  平均前期跌幅(drawdown_120d): {trades_df["drawdown_120d"].mean()*100:.2f}%')
print(f'  中位数: {trades_df["drawdown_120d"].median()*100:.2f}%')
print(f'  最大: {trades_df["drawdown_120d"].max()*100:.2f}%')

# ============================================================================
# 历史版本对比
# ============================================================================

print('\n' + '='*80)
print('📊 历史版本演进对比')
print('='*80)

print('\n版本演进:')
print(f'{"版本":<25} {"信号数":<10} {"平均收益":<12} {"盈利率":<10} {"止损率":<10} {"30%达成"}')
print('-'*80)

versions = [
    ('V3: 初版（未去重）', 12457, 0.69, 53.7, 37.0, 1.5),
    ('V5: 去重版', 668, 1.42, 54.0, 37.6, 1.8),
    ('V6: +drawdown_60d≥0.15', 537, 1.13, 58.3, 35.6, 1.5),
    (f'最终版: 优化参数', 
     len(trades_df), 
     trades_df['return'].mean()*100,
     len(profitable)/len(trades_df)*100,
     exit_reasons.get('止损-20%', 0)/len(trades_df)*100,
     (trades_df['return'] >= 0.30).mean()*100),
]

for ver, sig_count, avg_ret, profit_rate, stop_rate, rate_30 in versions:
    print(f'{ver:<25} {sig_count:<10} {avg_ret:<11.2f}% {profit_rate:<9.1f}% {stop_rate:<9.1f}% {rate_30:.1f}%')

# 计算改进
print(f'\n改进效果（vs V5 去重版）:')
baseline_return = 1.42
baseline_30pct = 1.8
baseline_stop = 37.6

current_return = trades_df['return'].mean() * 100
current_30pct = (trades_df['return'] >= 0.30).mean() * 100
current_stop = exit_reasons.get('止损-20%', 0)/len(trades_df)*100

if current_return > baseline_return:
    print(f'  ✅ 平均收益提升: {(current_return/baseline_return - 1)*100:+.1f}%')
else:
    print(f'  ❌ 平均收益下降: {(current_return/baseline_return - 1)*100:+.1f}%')

if current_30pct > baseline_30pct:
    print(f'  ✅ 30%达成率提升: {current_30pct - baseline_30pct:+.1f}个百分点')
else:
    print(f'  ❌ 30%达成率下降: {current_30pct - baseline_30pct:+.1f}个百分点')

if current_stop < baseline_stop:
    print(f'  ✅ 止损率降低: {baseline_stop - current_stop:+.1f}个百分点')
else:
    print(f'  ❌ 止损率上升: {current_stop - baseline_stop:+.1f}个百分点')

# ============================================================================
# 风险收益分析
# ============================================================================

print('\n' + '='*80)
print('📊 风险收益分析')
print('='*80)

盈利交易 = trades_df[trades_df['return'] > 0]
亏损交易 = trades_df[trades_df['return'] < 0]

print(f'\n盈利交易统计:')
print(f'  数量: {len(盈利交易)} 笔')
print(f'  平均盈利: {盈利交易["return"].mean()*100:.2f}%')
print(f'  中位数: {盈利交易["return"].median()*100:.2f}%')

print(f'\n亏损交易统计:')
print(f'  数量: {len(亏损交易)} 笔')
if len(亏损交易) > 0:
    print(f'  平均亏损: {亏损交易["return"].mean()*100:.2f}%')
    print(f'  中位数: {亏损交易["return"].median()*100:.2f}%')

# 盈亏比
if len(亏损交易) > 0:
    盈亏比 = abs(盈利交易["return"].mean() / 亏损交易["return"].mean())
    print(f'\n盈亏比: {盈亏比:.2f}')
    print(f'  解读: 平均盈利是平均亏损的 {盈亏比:.1f} 倍')

# ============================================================================
# 保存结果
# ============================================================================

output_file = '/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/requirements/FINAL_RESULTS.csv'
trades_df.to_csv(output_file, index=False)

print('\n' + '='*80)
print('✅ 最终验证完成')
print('='*80)

print(f'\n核心指标:')
print(f'  测试股票: {TEST_SIZE} 只')
print(f'  信号数: {len(trades_df)}')
print(f'  平均收益: {trades_df["return"].mean()*100:.2f}%')
print(f'  盈利率: {len(profitable)/len(trades_df)*100:.1f}%')
print(f'  30%达成率: {(trades_df["return"] >= 0.30).mean()*100:.1f}%')

print(f'\n✅ 详细结果已保存: FINAL_RESULTS.csv')

# ============================================================================
# 结论和建议
# ============================================================================

print('\n' + '='*80)
print('💡 最终结论')
print('='*80)

avg_ret = trades_df['return'].mean() * 100
rate_30 = (trades_df['return'] >= 0.30).mean() * 100

if avg_ret > 2.0 and rate_30 > 2.0:
    print('\n🎉 策略优化成功！')
    print(f'  平均收益: {avg_ret:.2f}%（目标>2%）')
    print(f'  30%达成率: {rate_30:.1f}%（目标>2%）')
    print('\n✅ 可以进入下一阶段:')
    print('  1. 扩大测试（500只股票）')
    print('  2. 集成到RTB.py')
    print('  3. 用回测框架验证')
    print('  4. 准备实盘')
elif avg_ret > 1.0:
    print('\n✅ 策略有效但仍需优化')
    print(f'  平均收益: {avg_ret:.2f}%')
    print(f'  30%达成率: {rate_30:.1f}%')
    print('\n建议:')
    print('  1. 调整目标为15-20%')
    print('  2. 或继续优化特征和参数')
else:
    print('\n⚠️ 策略表现不够理想')
    print(f'  平均收益: {avg_ret:.2f}%')
    print('\n建议重新考虑策略方向')

print('\n' + '='*80)
print('ML帮助我们发现的关键优化:')
print('='*80)
print('  1. ⭐ drawdown_120d >= 0.20（半年至少跌20%）')
print('  2. ⭐ 止损放宽到-20%')
print('  3. ⭐ 取消保本止损')
print('\n这些都是通过数据分析发现的！')
print('='*80)

