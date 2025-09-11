# HistoricLow 策略快速开始指南

## 🚀 快速开始

### 1. 基础模拟
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

### 2. 分析结果
```python
from app.analyzer.strategy.historicLow.strategy_analysis import HistoricLowAnalysis

# 创建分析器
analyzer = HistoricLowAnalysis()

# 获取最新模拟结果
latest_dir = analyzer.get_latest_session_dir()

# 加载投资数据
investments = analyzer.load_investment_data(latest_dir)

# 定义黑名单
blacklist = analyzer.define_blacklist(investments)
```

### 3. 资本模拟
```python
# 模拟10万资金投资
result = analyzer.compare_investment_methods(
    initial_capital=100000,
    start_date='2024-01-01'
)
```

## ⚙️ 主要配置

### 策略参数
```python
# 在 strategy_settings.py 中配置
strategy_settings = {
    "low_points_ref_years": [1, 3, 5, 8],  # 历史低点参考年份
    "invest_range": {
        "upper_bound": 0.10,  # 上方10%
        "lower_bound": 0.05   # 下方5%
    },
    "max_invest_slope": -0.056,  # 最大投资斜率
    "amplitude_filter": {
        "enabled": True,
        "min_amplitude": 0.10  # 最小振幅10%
    }
}
```

### 测试模式
```python
# 只测试问题股票
"test_problematic_stocks_only": True

# 限制测试股票数量
"max_test_stocks": 100
```

## 📊 结果解读

### 投资记录格式
```json
{
  "result": "win",           # 投资结果: win/loss/open
  "overall_profit_rate": 0.046,  # 总收益率: 4.6%
  "invest_duration_days": 266,    # 持有天数: 266天
  "slope_info": {
    "slope_ratio": -0.122    # 斜率: -12.2%
  }
}
```

### 会话汇总
- **总投资次数**: 模拟期间的总投资数量
- **胜率**: 盈利投资占总投资的百分比
- **平均收益率**: 所有投资的平均收益率
- **年化收益率**: 按年计算的收益率

## 🔧 常用命令

### 运行模拟
```bash
cd /Users/garnet/Desktop/stocks-py
source venv/bin/activate
python start.py
```

### 分析结果
```python
# 在Python中运行
from app.analyzer.strategy.historicLow.strategy_analysis import HistoricLowAnalysis
analyzer = HistoricLowAnalysis()
analyzer.analyze_distribution_by_time()
```

### 更新黑名单
```python
# 自动更新黑名单
simulator._update_blacklist_after_simulation()
```

## 🎯 策略特点

### 优势
- **多重过滤**: 通过振幅、斜率、波浪等条件过滤投资机会
- **动态止盈**: 采用分段止盈和动态止损机制
- **凯莉公式**: 支持基于历史表现的仓位管理
- **黑名单管理**: 自动识别和排除问题股票

### 适用场景
- **长期投资**: 适合中长期投资策略
- **价值投资**: 基于历史低点的价值投资
- **风险控制**: 多重过滤机制控制风险

## ⚠️ 注意事项

1. **数据质量**: 确保股票数据完整性和准确性
2. **参数调优**: 根据市场情况调整策略参数
3. **风险控制**: 注意投资风险，合理配置资金
4. **回测验证**: 充分回测验证策略有效性

## 📞 获取帮助

- 查看完整文档: `README.md`
- 检查配置: `strategy_settings.py`
- 分析结果: `strategy_analysis.py`
- 模拟器: `strategy_simulator.py`
