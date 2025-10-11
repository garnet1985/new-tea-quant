#!/usr/bin/env python3
"""
RTB 策略 - 训练XGBoost模型
目标：预测信号能否达到目标收益率
"""
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pickle

print('='*80)
print('RTB 策略 - XGBoost模型训练')
print('='*80)

# ============================================================================
# 加载数据
# ============================================================================

print('\n📊 Step 1: 加载训练数据...')

data_file = os.path.join(os.path.dirname(__file__), 'training_data.csv')
df = pd.read_csv(data_file)

print(f'✅ 加载了 {len(df)} 个样本')

# 特征列
feature_cols = [
    'ma_std', 'ma_bandwidth', 'position_20d', 'position_60d',
    'ma60slope', 'ma20slope', 'drawdown_20d', 'drawdown_60d',
    'return_5d', 'return_10d', 'return_20d',
    'volatility_5d', 'volatility_20d', 'volatility_60d',
    'volume_ratio', 'close_to_ma5', 'close_to_ma20', 'close_to_ma60',
    'ma5_above_ma20', 'ma20_above_ma60', 'price_above_ma60',
    'amplitude_20d'
]

# 检查特征是否都存在
missing = [col for col in feature_cols if col not in df.columns]
if len(missing) > 0:
    print(f'⚠️  缺失特征: {missing}')
    feature_cols = [col for col in feature_cols if col in df.columns]

print(f'特征数量: {len(feature_cols)}')

# ============================================================================
# 数据划分
# ============================================================================

print('\n📊 Step 2: 数据划分...')

# 按时间划分（更合理）
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

# 训练集：2015-2021 (70%)
# 验证集：2022 (15%)
# 测试集：2023-2024 (15%)

train_end = pd.to_datetime('2021-12-31')
val_end = pd.to_datetime('2022-12-31')

train_df = df[df['date'] <= train_end]
val_df = df[(df['date'] > train_end) & (df['date'] <= val_end)]
test_df = df[df['date'] > val_end]

print(f'训练集: {len(train_df)} 样本 ({train_df["date"].min().date()} ~ {train_df["date"].max().date()})')
print(f'验证集: {len(val_df)} 样本 ({val_df["date"].min().date()} ~ {val_df["date"].max().date()})')
print(f'测试集: {len(test_df)} 样本 ({test_df["date"].min().date()} ~ {test_df["date"].max().date()})')

# ============================================================================
# 训练多个模型（不同目标）
# ============================================================================

targets = {
    '10%': 'label_10',
    '20%': 'label_20',
    '30%': 'label_30',
}

models = {}

for target_name, label_col in targets.items():
    print('\n' + '='*80)
    print(f'📊 训练模型: 预测能否达到 {target_name}')
    print('='*80)
    
    # 准备数据
    X_train = train_df[feature_cols].values
    y_train = train_df[label_col].values
    
    X_val = val_df[feature_cols].values
    y_val = val_df[label_col].values
    
    X_test = test_df[feature_cols].values
    y_test = test_df[label_col].values
    
    # 检查类别平衡
    print(f'\n训练集标签分布:')
    print(f'  正样本(达到{target_name}): {y_train.sum()} ({y_train.mean()*100:.1f}%)')
    print(f'  负样本(未达到): {len(y_train) - y_train.sum()} ({(1-y_train.mean())*100:.1f}%)')
    
    # 处理类别不平衡
    scale_pos_weight = (len(y_train) - y_train.sum()) / y_train.sum()
    
    # 训练XGBoost
    print(f'\n开始训练...')
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,  # 处理类别不平衡
        random_state=42,
        eval_metric='logloss'
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    # 评估
    y_pred_train = model.predict(X_train)
    y_pred_val = model.predict(X_val)
    y_pred_test = model.predict(X_test)
    
    y_pred_proba_test = model.predict_proba(X_test)[:, 1]
    
    print(f'\n模型评估:')
    print(f'  训练集准确率: {(y_pred_train == y_train).mean()*100:.2f}%')
    print(f'  验证集准确率: {(y_pred_val == y_val).mean()*100:.2f}%')
    print(f'  测试集准确率: {(y_pred_test == y_test).mean()*100:.2f}%')
    
    if len(np.unique(y_test)) == 2:  # 确保两个类别都存在
        auc = roc_auc_score(y_test, y_pred_proba_test)
        print(f'  测试集AUC: {auc:.4f}')
    
    # 混淆矩阵
    cm = confusion_matrix(y_test, y_pred_test)
    print(f'\n混淆矩阵（测试集）:')
    print(f'              预测：不达标  预测：达标')
    print(f'实际：不达标    {cm[0,0]:<10}  {cm[0,1]:<10}')
    print(f'实际：达标      {cm[1,0]:<10}  {cm[1,1]:<10}')
    
    # 计算精确率和召回率
    if cm[1,1] + cm[0,1] > 0:
        precision = cm[1,1] / (cm[1,1] + cm[0,1])
        print(f'\n精确率（预测达标的准确性）: {precision*100:.2f}%')
    
    if cm[1,1] + cm[1,0] > 0:
        recall = cm[1,1] / (cm[1,1] + cm[1,0])
        print(f'召回率（找出多少达标的）: {recall*100:.2f}%')
    
    # 保存模型
    model_file = os.path.join(os.path.dirname(__file__), f'models/rtb_xgboost_{target_name.replace("%","pct")}.pkl')
    os.makedirs(os.path.dirname(model_file), exist_ok=True)
    
    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'feature_cols': feature_cols,
            'target': target_name,
        }, f)
    
    print(f'\n✅ 模型已保存: {model_file}')
    
    models[target_name] = model

# ============================================================================
# 特征重要性分析
# ============================================================================

print('\n' + '='*80)
print('📊 特征重要性分析（30%目标模型）')
print('='*80)

model_30 = models['30%']
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model_30.feature_importances_
}).sort_values('importance', ascending=False)

print('\nTop 10 最重要特征:')
print('-'*60)
for idx, row in feature_importance.head(10).iterrows():
    print(f'{row["feature"]:<25} {row["importance"]:.4f}')

# 绘制特征重要性
fig, ax = plt.subplots(figsize=(10, 8))
top_features = feature_importance.head(15)
ax.barh(range(len(top_features)), top_features['importance'])
ax.set_yticks(range(len(top_features)))
ax.set_yticklabels(top_features['feature'])
ax.set_xlabel('Importance')
ax.set_title('Top 15 Feature Importance (30% Target Model)')
ax.invert_yaxis()
plt.tight_layout()

importance_plot = os.path.join(os.path.dirname(__file__), 'feature_importance.png')
plt.savefig(importance_plot, dpi=150)
print(f'\n✅ 特征重要性图已保存: feature_importance.png')

# ============================================================================
# 测试模型实际效果
# ============================================================================

print('\n' + '='*80)
print('📊 模型实际应用测试')
print('='*80)

# 用30%模型在测试集上筛选
print('\n【30%目标模型】')
print('-'*80)

y_pred_proba = model_30.predict_proba(X_test)[:, 1]

# 不同概率阈值的效果
thresholds = [0.50, 0.60, 0.70, 0.80, 0.90]

print(f'\n不同概率阈值的精确率:')
print(f'{"阈值":<10} {"选中数":<10} {"达标数":<10} {"精确率":<15} {"召回率"}')
print('-'*60)

for threshold in thresholds:
    selected = y_pred_proba >= threshold
    selected_count = selected.sum()
    
    if selected_count == 0:
        print(f'{threshold:<10.2f} {0:<10} {0:<10} {"N/A":<15} {"N/A"}')
        continue
    
    达标数 = y_test[selected].sum()
    精确率 = 达标数 / selected_count if selected_count > 0 else 0
    召回率 = 达标数 / y_test.sum() if y_test.sum() > 0 else 0
    
    print(f'{threshold:<10.2f} {selected_count:<10} {达标数:<10} {精确率*100:<14.1f}% {召回率*100:.1f}%')

print('\n' + '='*80)
print('✅ 模型训练完成！')
print('='*80)

print(f'\n产出文件:')
print(f'  - rtb_xgboost_10pct.pkl  （10%目标模型）')
print(f'  - rtb_xgboost_20pct.pkl  （20%目标模型）')
print(f'  - rtb_xgboost_30pct.pkl  （30%目标模型）')
print(f'  - feature_importance.png （特征重要性图）')

print(f'\n下一步:')
print(f'  1. 查看特征重要性，了解哪些特征最关键')
print(f'  2. 调整概率阈值，平衡精确率和召回率')
print(f'  3. 集成到RTB.py进行回测验证')

print('\n' + '='*80)

