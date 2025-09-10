# HistoricLow 历史低点投资策略

## 📋 投资策略概述

HistoricLow策略是一个基于历史低点识别的股票投资策略。该策略通过分析股票的历史价格走势，识别具有投资价值的低点位置，并在合适的时机进行投资，实现长期稳定的投资收益。

## 🎯 投资原理

### 核心投资理念
1. **历史低点识别**：基于2年、4年、6年、8年的历史数据识别关键低点
2. **投资范围控制**：在历史低点上方10%和下方5%的范围内寻找投资机会
3. **多重过滤机制**：通过振幅、斜率、波浪完整性等多重条件过滤投资机会
4. **动态止盈止损**：采用分段止盈和动态止损机制

### 投资逻辑
- **低点支撑**：历史低点往往具有强支撑作用，价格触及后容易反弹
- **价值回归**：当价格接近历史低点时，存在价值回归的投资机会
- **风险控制**：通过多重过滤条件控制投资风险，提高投资成功率

## 🏗️ 文件结构

```
app/analyzer/strategy/historicLow/
├── README.md                    # 策略说明文档
├── strategy.py                  # 主策略逻辑
├── strategy_service.py          # 策略服务层
├── strategy_simulator.py        # 策略模拟器
├── strategy_analysis.py         # 策略分析工具
├── strategy_settings.py         # 策略配置
└── tmp/                         # 模拟结果存储
```

## ⚙️ 投资设置说明

### 历史低点识别设置
```python
"low_points_ref_years": [1, 3, 5, 8]  # 参考年份：1年、3年、5年、8年
```
**说明**: 策略会基于这些年份的历史数据识别关键低点。更多年份提供更全面的历史参考，但可能错过短期机会。

### 投资范围设置
```python
"invest_range": {
    "upper_bound": 0.10,  # 历史低点上方10%
    "lower_bound": 0.05   # 历史低点下方5%
}
```
**说明**: 只有在历史低点上方10%和下方5%的范围内才会考虑投资。这个范围可以根据市场波动性调整。

### 冻结期设置
```python
"freeze_period": {
    "days": 30,              # 冻结期30天
    "max_touch_times": 1     # 最多接触1次
}
```
**说明**: 在冻结期内，同一低点最多只能接触1次，避免重复投资同一位置。

### 投资过滤设置

#### 振幅过滤
```python
"amplitude_filter": {
    "enabled": True,
    "min_amplitude": 0.10  # 最小振幅10%
}
```
**说明**: 过滤掉振幅过小的投资机会，确保有足够的波动空间。

#### 斜率过滤
```python
"max_invest_slope": -0.056  # 最大投资斜率（约-5度）
```
**说明**: 只投资斜率小于-5度的机会，过滤掉过于平缓的走势。

#### 波浪过滤
```python
"wave_filter": {
    "enabled": True,
    "min_wave_days": 30  # 最小波浪天数
}
```
**说明**: 确保历史低点后有完整的波浪结构，提高投资可靠性。

### 资金管理设置

#### 凯莉公式配置
```python
"kelly_formula": {
    "enabled": True,
    "min_capital_threshold": 200000,  # 资金超过20万时启用
    "min_kelly_fraction": 0.05,       # 最小投资比例5%
    "max_kelly_fraction": 0.30,       # 最大投资比例30%
    "default_win_rate": 0.5,          # 默认胜率50%
    "default_avg_win": 0.15,          # 默认平均盈利15%
    "default_avg_loss": -0.08         # 默认平均亏损-8%
}
```
**说明**: 当资金超过20万时，自动使用凯莉公式进行仓位管理，根据历史表现动态调整投资比例。

#### 投资过滤配置
```python
"investment_filter": {
    "enabled": True,
    "min_capital_threshold": 500000,  # 资金小于50万时启用
    "min_roi_threshold": 0.05         # 最小收益率阈值5%
}
```
**说明**: 当资金较小时，只投资预期收益率大于5%的机会，提高资金利用效率。

## 🔧 投资方法详解

### 1. 历史低点识别方法
策略通过分析股票的历史价格数据，识别出具有投资价值的关键低点：

- **多时间维度分析**: 同时考虑1年、3年、5年、8年的历史数据
- **低点质量评估**: 评估低点的可靠性和支撑强度
- **动态更新**: 随着新数据的加入，动态更新低点识别结果

### 2. 投资机会识别
当股票价格接近历史低点时，策略会评估是否具备投资条件：

- **价格范围检查**: 价格必须在历史低点上方10%和下方5%的范围内
- **时间窗口控制**: 在冻结期内，同一低点最多只能接触1次
- **市场环境评估**: 考虑当前的市场环境和波动情况

### 3. 多重过滤机制
为了确保投资质量，策略采用多重过滤条件：

- **振幅过滤**: 确保有足够的波动空间，过滤掉振幅过小的机会
- **斜率过滤**: 只投资斜率小于-5度的机会，避免过于平缓的走势
- **波浪过滤**: 确保历史低点后有完整的波浪结构
- **多次接触过滤**: 限制同一低点的接触次数，避免重复投资

### 4. 动态止盈止损
策略采用分段止盈和动态止损机制：

- **分段止盈**: 根据价格涨幅分阶段止盈，锁定部分收益
- **动态止损**: 根据市场情况动态调整止损位置
- **风险控制**: 严格控制单笔投资的最大亏损

## 📊 投资模拟方法

### 1. 基础模拟
模拟策略在历史数据上的表现，验证投资方法的有效性：

```python
# 导入必要模块
from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
from app.analyzer.strategy.historicLow.strategy_simulator import HLSimulator

# 创建策略和模拟器
strategy = HistoricLowStrategy()
simulator = HLSimulator(strategy)

# 准备股票列表
stocks = [
    {'id': '000001.SZ', 'name': '平安银行'},
    {'id': '000002.SZ', 'name': '万科A'},
    # ... 更多股票
]

# 运行模拟
results = simulator.run_jobs(stocks)
```

### 2. 资本模拟
模拟真实资金的投资效果，包括资金管理和仓位控制：

```python
from app.analyzer.strategy.historicLow.strategy_analysis import HistoricLowAnalysis

# 创建分析器
analyzer = HistoricLowAnalysis()

# 模拟10万资金从2024年1月开始投资
result = analyzer.compare_investment_methods(
    initial_capital=100000,  # 初始资金10万
    start_date='2024-01-01'  # 开始日期
)
```

### 3. 投资结果分析
分析模拟结果，了解策略的投资表现：

- **胜率统计**: 计算投资成功的比例
- **收益率分析**: 分析平均收益率和年化收益率
- **风险控制**: 评估最大回撤和风险控制效果
- **时间分布**: 分析不同时期的投资表现

### 4. 黑名单管理
自动识别和排除表现不佳的股票：

- **自动识别**: 基于胜率和收益率自动识别问题股票
- **动态更新**: 模拟完成后自动更新黑名单
- **配置同步**: 自动更新策略配置文件

## 🚀 使用方法

### 1. 基础模拟
```python
from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
from app.analyzer.strategy.historicLow.strategy_simulator import HLSimulator

# 创建策略和模拟器
strategy = HistoricLowStrategy()
simulator = HLSimulator(strategy)

# 运行模拟
results = simulator.run_jobs(stock_list)
```

### 2. 黑名单更新
```python
from app.analyzer.strategy.historicLow.strategy_analysis import HistoricLowAnalysis

# 创建分析器
analyzer = HistoricLowAnalysis()

# 更新黑名单
new_blacklist = analyzer.define_blacklist(investments)
```

### 3. 资本模拟
```python
# 模拟10万资金从2024年1月开始投资
result = analyzer.compare_investment_methods(
    initial_capital=100000,
    start_date='2024-01-01'
)
```

## 📋 配置说明

### 策略参数
- `low_points_ref_years`: 历史低点参考年份
- `invest_range`: 投资范围配置
- `freeze_period`: 冻结期配置
- `amplitude_filter`: 振幅过滤配置
- `max_invest_slope`: 最大投资斜率
- `kelly_formula`: 凯莉公式配置
- `investment_filter`: 投资过滤配置

### 测试模式
- `test_problematic_stocks_only`: 是否只测试问题股票
- `max_test_stocks`: 最大测试股票数量

### 黑名单配置
- `problematic_stocks`: 问题股票列表
- 支持自动更新和手动维护

## 🔍 性能优化

### 多进程处理
- 使用`ProcessWorker`进行并行处理
- 支持队列模式和批处理模式
- 自动负载均衡

### 内存管理
- 按需加载股票数据
- 及时释放不需要的数据
- 优化数据结构

### 错误处理
- 完善的异常处理机制
- 除0错误防护
- 数据验证和清理

## 📊 结果分析

### 模拟结果格式
```json
{
  "stock_info": {
    "id": "000001.SZ",
    "name": "平安银行"
  },
  "investments": {
    "investment_1": {
      "result": {
        "result": "win",
        "overall_profit_rate": 0.046,
        "invest_duration_days": 266
      },
      "slope_info": {
        "slope_ratio": -0.122
      }
    }
  }
}
```

### 会话汇总
- 总投资次数
- 胜率统计
- 平均收益率
- 年化收益率
- 投资分布

## 🛠️ 开发指南

### 添加新过滤条件
1. 在`strategy_service.py`中实现过滤逻辑
2. 在`strategy.py`中集成过滤条件
3. 在`strategy_settings.py`中添加配置

### 扩展分析功能
1. 在`strategy_analysis.py`中添加分析方法
2. 实现数据加载和处理逻辑
3. 添加结果输出格式

### 优化性能
1. 使用多进程处理
2. 优化数据结构和算法
3. 添加缓存机制

## 📝 更新日志

### v1.0.0 (2025-09-10)
- 初始版本发布
- 实现基础历史低点策略
- 支持多重过滤机制
- 集成凯莉公式
- 添加黑名单管理
- 完善模拟和分析功能

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件
- 参与讨论

---

**注意**: 本策略仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。
