#!/usr/bin/env python3
"""
RTB 策略 - 准备ML训练数据
从全市场股票中提取特征和标签
"""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from feature_engineer import RTBFeatureEngineer
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader
from tqdm import tqdm

print('='*80)
print('RTB 策略 - 准备ML训练数据')
print('='*80)

# ============================================================================
# 配置
# ============================================================================

# 训练数据范围
SAMPLE_SIZE = 200  # 先用200只股票（可以调整到500-1000）
START_DATE = '20150101'
END_DATE = ''

# 去重配置
DEDUPLICATE = True
COOLING_PERIOD = 120

print(f'\n配置:')
print(f'  股票数量: {SAMPLE_SIZE}')
print(f'  时间范围: {START_DATE} - {END_DATE if END_DATE else "最新"}')
print(f'  信号去重: {DEDUPLICATE}')
print(f'  冷却期: {COOLING_PERIOD}天')

# ============================================================================
# 加载股票列表
# ============================================================================

print('\n📊 Step 1: 加载股票列表...')

db = DatabaseManager(is_verbose=False)
db.initialize()

loader = DataLoader(db)
stock_list = loader.load_stock_list()

# 随机采样（确保多样性）
np.random.seed(42)
if len(stock_list) > SAMPLE_SIZE:
    sample_indices = np.random.choice(len(stock_list), SAMPLE_SIZE, replace=False)
    sampled_stocks = [stock_list[i] for i in sample_indices]
else:
    sampled_stocks = stock_list

print(f'✅ 将处理 {len(sampled_stocks)} 只股票')

# 统计市场分布
market_stats = {}
for stock in sampled_stocks:
    stock_id = stock['id']
    if stock_id.startswith('60'):
        market = '上证'
    elif stock_id.startswith('30'):
        market = '创业板'
    elif stock_id.startswith('00'):
        market = '深证主板'
    else:
        market = '其他'
    
    market_stats[market] = market_stats.get(market, 0) + 1

print('\n市场分布:')
for market, count in market_stats.items():
    print(f'  {market}: {count} 只')

# ============================================================================
# 批量提取特征
# ============================================================================

print('\n📊 Step 2: 批量提取特征和标签...')

engineer = RTBFeatureEngineer()
all_training_data = []
failed_stocks = []

for i, stock in enumerate(tqdm(sampled_stocks, desc="处理进度")):
    stock_id = stock['id']
    stock_name = stock['name']
    
    try:
        # 加载K线
        klines = loader.load_klines(
            stock_id=stock_id,
            term='daily',
            start_date=START_DATE,
            end_date=END_DATE,
            adjust='qfq'
        )
        
        if len(klines) < 200:
            failed_stocks.append((stock_name, '数据不足'))
            continue
        
        df = pd.DataFrame(klines)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        df['stock_id'] = stock_id
        df['stock_name'] = stock_name
        
        # 提取特征和标签
        stock_data = engineer.prepare_training_data(
            df, 
            deduplicate=DEDUPLICATE,
            cooling_period=COOLING_PERIOD
        )
        
        if len(stock_data) > 0:
            all_training_data.append(stock_data)
        else:
            failed_stocks.append((stock_name, '无符合条件的信号'))
        
    except Exception as e:
        failed_stocks.append((stock_name, str(e)))
        continue

print(f'\n✅ 成功处理: {len(all_training_data)} 只股票')
print(f'⚠️  失败: {len(failed_stocks)} 只股票')

if len(failed_stocks) > 0 and len(failed_stocks) <= 10:
    print('\n失败原因:')
    for name, reason in failed_stocks[:10]:
        print(f'  {name}: {reason}')

if len(all_training_data) == 0:
    print('\n❌ 没有成功提取任何训练数据')
    sys.exit(1)

# ============================================================================
# 合并数据
# ============================================================================

print('\n📊 Step 3: 合并数据...')

training_df = pd.concat(all_training_data, ignore_index=True)

print(f'✅ 总样本数: {len(training_df)}')

# 统计标签分布
print(f'\n标签分布:')
print(f'  能涨10%: {training_df["label_10"].sum()} ({training_df["label_10"].mean()*100:.1f}%)')
print(f'  能涨15%: {training_df["label_15"].sum()} ({training_df["label_15"].mean()*100:.1f}%)')
print(f'  能涨20%: {training_df["label_20"].sum()} ({training_df["label_20"].mean()*100:.1f}%)')
print(f'  能涨30%: {training_df["label_30"].sum()} ({training_df["label_30"].mean()*100:.1f}%)')

# ============================================================================
# 数据清洗
# ============================================================================

print('\n📊 Step 4: 数据清洗...')

# 删除包含NaN的行
before_count = len(training_df)
training_df = training_df.dropna()
after_count = len(training_df)

if before_count > after_count:
    print(f'⚠️  删除了 {before_count - after_count} 行包含NaN的数据')

print(f'✅ 清洗后样本数: {len(training_df)}')

# ============================================================================
# 保存数据
# ============================================================================

print('\n📊 Step 5: 保存训练数据...')

# 选择需要的列
feature_cols = engineer.get_feature_columns()
label_cols = ['label_10', 'label_15', 'label_20', 'label_30', 'future_max_return']
meta_cols = ['stock_id', 'stock_name', 'date', 'close']

# 检查列是否都存在
missing_cols = [col for col in feature_cols if col not in training_df.columns]
if len(missing_cols) > 0:
    print(f'⚠️  缺失特征: {missing_cols}')
    feature_cols = [col for col in feature_cols if col in training_df.columns]

output_cols = meta_cols + feature_cols + label_cols
training_data = training_df[output_cols].copy()

# 保存
output_file = os.path.join(os.path.dirname(__file__), 'training_data.csv')
training_data.to_csv(output_file, index=False)

print(f'✅ 训练数据已保存: training_data.csv')
print(f'   样本数: {len(training_data)}')
print(f'   特征数: {len(feature_cols)}')
print(f'   文件大小: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB')

# ============================================================================
# 数据统计
# ============================================================================

print('\n' + '='*80)
print('📊 训练数据统计')
print('='*80)

print(f'\n样本分布:')
print(f'  总样本数: {len(training_data)}')
print(f'  正样本(10%): {training_data["label_10"].sum()} ({training_data["label_10"].mean()*100:.1f}%)')
print(f'  正样本(20%): {training_data["label_20"].sum()} ({training_data["label_20"].mean()*100:.1f}%)')
print(f'  正样本(30%): {training_data["label_30"].sum()} ({training_data["label_30"].mean()*100:.1f}%)')

print(f'\n特征列表 ({len(feature_cols)}个):')
for i, col in enumerate(feature_cols, 1):
    print(f'  {i:2d}. {col}')

print(f'\n标签列表:')
for col in label_cols:
    print(f'  - {col}')

print('\n特征统计:')
print(training_data[feature_cols].describe().T[['mean', 'std', 'min', 'max']].to_string())

print('\n' + '='*80)
print('✅ 数据准备完成！')
print('='*80)

print(f'\n下一步:')
print(f'  1. 查看 training_data.csv')
print(f'  2. 运行 train_model.py 训练模型')
print(f'  3. 评估模型效果')

print('\n' + '='*80)

