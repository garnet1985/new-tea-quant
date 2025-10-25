# MeanReversion 策略

## 📖 策略概述

MeanReversion（均值回归）策略基于统计学中的均值回归理论，认为股票价格不会长期偏离其均线太远，当偏离达到极端水平时会发生回归。

## 🎯 核心思想

- **均值回归原理**：股票价格围绕均线波动，极端偏离后会回归
- **动态阈值**：使用历史分位数动态定义"极端"水平，而非固定阈值
- **相对偏离**：使用相对偏离率消除不同股票绝对价格的差异

## 🔧 算法逻辑

### 1. 数据预处理
```python
# 计算均线
ma = close.rolling(ma_period).mean()

# 计算价格标准差（波动性指标）
std = close.rolling(std_period).std()

# 计算相对偏离率
deviation = (close - ma) / ma
```

### 2. 动态阈值计算
```python
# 计算历史分位数边界
lower_bound = deviation.rolling(quantile_period).quantile(lower_quantile)
upper_bound = deviation.rolling(quantile_period).quantile(upper_quantile)
```

### 3. 信号生成
```python
# 买入信号：当前偏离率低于历史5%分位数
signal_buy = deviation < lower_bound

# 卖出信号：当前偏离率高于历史95%分位数  
signal_sell = deviation > upper_bound
```

## 📊 参数配置

### Core 参数
- `ma_period`: 均线周期（默认：20天）
- `std_period`: 标准差计算周期（默认：20天）
- `quantile_period`: 分位数计算周期（默认：120天）
- `lower_quantile`: 下分位数（默认：0.05，即5%）
- `upper_quantile`: 上分位数（默认：0.95，即95%）

### 风险控制
- `stop_loss`: 止损百分比（默认：-8%）

## 🎯 策略特点

### 优势
- **自适应性强**：动态阈值适应不同股票的波动特性
- **统计基础**：基于历史数据分布，非主观判断
- **跨股票稳定**：相对偏离率消除绝对价格差异
- **适合震荡市场**：在横盘整理中表现优异

### 劣势
- **趋势市场风险**：在强趋势中可能频繁止损
- **数据依赖**：需要足够的历史数据计算分位数
- **滞后性**：基于历史数据，可能错过快速反转

## 📈 适用场景

- **震荡市场**：价格在区间内波动的市场环境
- **高波动股票**：波动性较大的个股
- **短期交易**：持仓时间通常较短
- **统计套利**：利用价格回归特性的量化策略

## ⚠️ 风险提示

1. **数据要求**：需要至少120天历史数据
2. **趋势风险**：在强趋势市场中可能表现不佳
3. **止损风险**：8%止损可能过于严格或宽松
4. **参数敏感**：分位数周期和均线周期需要优化

## 🔍 算法详解

### 偏离率计算
```
deviation = (close - ma) / ma
```
- 正值：价格高于均线
- 负值：价格低于均线
- 绝对值：偏离程度

### 分位数边界
- **5%分位数**：过去120天中，只有5%的时间偏离率比这个值更低
- **95%分位数**：过去120天中，只有5%的时间偏离率比这个值更高

### 信号逻辑
- **买入**：当前偏离率 < 5%分位数（极端低估）
- **卖出**：当前偏离率 > 95%分位数（极端高估）

## 📁 文件结构

```
MeanReversion/
├── README.md           # 策略说明文档
├── MeanReversion.py    # 策略实现
└── settings.py         # 参数配置
```

## 🔧 实现细节

### 买入信号生成
```python
# 检查数据长度
if len(klines) < quantile_period:
    return None

# 计算技术指标
df['ma'] = df['close'].rolling(window=ma_period).mean()
df['deviation'] = (df['close'] - df['ma']) / df['ma']
df['lower_bound'] = df['deviation'].rolling(window=quantile_period).quantile(lower_quantile)

# 生成买入信号
if latest['deviation'] < latest['lower_bound']:
    return opportunity
```

### 卖出信号生成
```python
# 检查止损
if current_roi <= stop_loss:
    return True, investment  # 止损卖出

# 检查均值回归卖出信号
df['upper_bound'] = df['deviation'].rolling(window=quantile_period).quantile(upper_quantile)
if latest['deviation'] > latest['upper_bound']:
    return True, investment  # 回归卖出
```

### 机会特征
- `current_deviation`: 当前偏离率
- `lower_bound`: 历史5%分位数
- `ma_value`: 均线值
- `current_price`: 当前价格
- `volatility`: 价格波动性
- `deviation_percentile`: 当前偏离率的历史分位数

## 🚀 使用示例

```python
# 策略配置示例
core = {
    "ma_period": 20,
    "std_period": 20, 
    "quantile_period": 120,
    "lower_quantile": 0.05,
    "upper_quantile": 0.95
}

goal = {
    "stop_loss": -0.08,  # -8%止损
    "is_customized": True
}
```

## 📚 理论基础

- **均值回归理论**：价格围绕均值波动的统计现象
- **分位数回归**：使用历史分位数定义异常值
- **相对强弱指标**：消除绝对价格差异的相对比较
- **统计套利**：利用价格回归特性的量化交易策略
