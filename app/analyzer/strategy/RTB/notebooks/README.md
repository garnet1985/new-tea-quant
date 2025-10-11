# RTB 策略 - 机器学习实验

## 🎯 目标

使用 XGBoost 机器学习模型来识别反转趋势的买入机会。

## 📚 什么是 Jupyter Notebook？

**Jupyter Notebook** 是一个交互式编程环境，特别适合：
- ✅ **边写边看结果** - 不用等整个脚本运行完
- ✅ **可视化数据** - 图表、表格直接显示
- ✅ **实验调试** - 修改一部分，只重新运行那部分
- ✅ **记录思路** - 代码和markdown混合，就像日记本

**对比：**
```
传统Python脚本          Jupyter Notebook
─────────────          ────────────────
写完整个文件            分块执行（Cell）
运行全部看结果          实时查看每一步
修改要重新全部运行      只重新运行需要的部分
只能print输出           图表直接显示
```

## 🚀 快速开始

### 方案 A: 运行演示脚本（推荐新手）

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 进入目录
cd app/analyzer/strategy/RTB/notebooks

# 3. 运行演示
python rtb_feature_demo.py
```

这个脚本会：
1. 加载一只测试股票的数据
2. 计算RTB特征（均线收敛、价格位置等）
3. 分析信号点的有效性
4. 生成可视化图表
5. 保存处理后的数据

### 方案 B: 使用 Jupyter Notebook（推荐有经验者）

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 启动 Jupyter
jupyter notebook

# 3. 在浏览器中打开
# 会自动打开浏览器，显示文件列表
# 点击 01_rtb_feature_exploration.ipynb

# 4. 运行 Cell
# 按 Shift+Enter 运行当前 Cell 并跳到下一个
# 或点击上方的 "Run" 按钮
```

**Jupyter 快捷键：**
- `Shift + Enter` - 运行当前 Cell 并移动到下一个
- `Ctrl + Enter` - 运行当前 Cell 但停留在原地
- `A` - 在上方插入新 Cell
- `B` - 在下方插入新 Cell
- `DD` - 删除当前 Cell
- `M` - 切换到 Markdown 模式
- `Y` - 切换到代码模式

## 📊 文件说明

- `rtb_feature_demo.py` - Python演示脚本（适合快速测试）
- `01_rtb_feature_exploration.ipynb` - Jupyter Notebook（适合交互式实验）
- `rtb_feature_analysis.png` - 生成的特征分析图表
- `rtb_return_distribution.png` - 收益率分布图表

## 🔬 实验流程

### 第一阶段：特征探索（当前）

1. **单只股票实验**
   - 加载数据
   - 计算特征
   - 可视化观察
   - 分析有效性

2. **多只股票验证**
   - 选择10-20只代表性股票
   - 验证特征普遍性
   - 调整参数

### 第二阶段：数据准备（下一步）

1. 提取全市场股票特征
2. 计算标签（未来收益率）
3. 数据清洗和验证
4. 划分训练/验证/测试集

### 第三阶段：模型训练

1. 训练 XGBoost 模型
2. 特征重要性分析
3. 超参数调优
4. 模型评估

### 第四阶段：策略集成

1. 将模型集成到 RTB.py
2. 回测验证
3. 参数优化

## 🎨 核心特征说明

### 1. 均线收敛度（ma_std）
```python
# 4条均线的标准差，越小越收敛
ma_std = std([ma5, ma10, ma20, ma60]) / close

# 典型阈值：< 0.02 表示收敛
```

### 2. 价格位置（price_position）
```python
# 价格在20日震荡区间的位置
price_position = (close - low_20d) / (high_20d - low_20d)

# 0 = 区间底部
# 1 = 区间顶部
# < 0.33 = 下1/3（低位）
```

### 3. 趋势特征（trend_recent_20d）
```python
# 最近20天的涨跌幅
trend_recent_20d = (close - close_20d_ago) / close_20d_ago

# 接近0表示平稳
# 负值表示下跌
```

## 📈 标签定义

### 回归标签（推荐）
```python
# 未来N天的最大收益率
future_return_10d = (max_future_10d - current_close) / current_close
```

### 二分类标签
```python
# 未来是否涨>30%
label_10d = 1 if future_return_10d > 0.30 else 0
```

## 💡 实验建议

1. **先用1只股票** - 熟悉流程
2. **观察图表** - 找出模式
3. **调整阈值** - 看效果变化
4. **增加特征** - 添加RSI、MACD等
5. **扩展到多只** - 验证普遍性

## 🆘 常见问题

### Q1: Jupyter 启动后浏览器没有自动打开？
```bash
# 手动复制链接到浏览器
# 终端会显示类似：
# http://localhost:8888/?token=xxxxx
```

### Q2: 图表不显示？
```bash
# 在 Notebook 开头添加：
%matplotlib inline
```

### Q3: 运行很慢？
```bash
# 减少数据量：
start_date='20200101'  # 只用最近几年数据
```

### Q4: 内存不够？
```bash
# 一次只处理一部分股票：
stock_list[:100]  # 只用前100只
```

## 📝 下一步计划

- [ ] 完成单只股票特征探索
- [ ] 扩展到10-20只股票验证
- [ ] 编写批量特征提取脚本
- [ ] 准备训练数据集
- [ ] 训练第一个 XGBoost 模型
- [ ] 评估模型效果
- [ ] 集成到策略中

## 📚 参考资料

- XGBoost 文档: https://xgboost.readthedocs.io/
- Jupyter 教程: https://jupyter.org/try
- Pandas 可视化: https://pandas.pydata.org/docs/user_guide/visualization.html

