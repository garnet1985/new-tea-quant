# HistoricLow 策略性能分析

## 📊 策略性能指标

### 1. 基础性能指标
- **胜率**: 盈利投资占总投资的百分比
- **平均收益率**: 所有投资的平均收益率
- **年化收益率**: 按年计算的收益率
- **最大回撤**: 投资期间的最大亏损幅度
- **夏普比率**: 风险调整后的收益率

### 2. 投资分布指标
- **投资次数**: 总体的投资频率
- **投资分布**: 按年、月的投资分布
- **持仓时间**: 平均持仓天数
- **止盈止损**: 止盈和止损的比例

### 3. 风险控制指标
- **黑名单股票**: 表现不佳的股票数量
- **过滤效果**: 各种过滤条件的效果
- **资金利用率**: 资金的使用效率

## 📈 性能分析方法

### 1. 时间分布分析
```python
from app.analyzer.strategy.historicLow.strategy_analysis import HistoricLowAnalysis

analyzer = HistoricLowAnalysis()
analyzer.analyze_distribution_by_time()
```

**分析内容**:
- 按年分析投资分布和收益率
- 按月分析投资分布和收益率
- 识别最佳和最差的投资时期

### 2. 黑名单分析
```python
# 定义黑名单
blacklist = analyzer.define_blacklist(
    investments=investments,
    min_investments=3,
    max_win_rate=30.0,
    max_avg_profit=-5.0
)

# 分析黑名单变化
changes = analyzer.analyze_blacklist_changes(old_blacklist, new_blacklist)
```

**分析内容**:
- 识别问题股票
- 分析黑名单变化趋势
- 评估过滤效果

### 3. 资本模拟分析
```python
# 模拟不同资金规模的投资效果
result_100k = analyzer.compare_investment_methods(initial_capital=100000)
result_500k = analyzer.compare_investment_methods(initial_capital=500000)
result_1m = analyzer.compare_investment_methods(initial_capital=1000000)
```

**分析内容**:
- 不同资金规模的投资效果
- 凯莉公式vs固定投资的效果对比
- 资金利用率分析

## 🔍 性能优化建议

### 1. 参数优化
- **历史低点年份**: 根据市场特点调整参考年份
- **投资范围**: 根据波动率调整投资范围
- **过滤条件**: 根据市场环境调整过滤阈值

### 2. 过滤条件优化
- **振幅过滤**: 提高振幅阈值过滤低质量机会
- **斜率过滤**: 调整斜率阈值控制投资时机
- **波浪过滤**: 确保投资机会的可靠性

### 3. 风险管理优化
- **黑名单管理**: 及时更新和清理黑名单
- **资金管理**: 使用凯莉公式优化仓位
- **止盈止损**: 优化止盈止损策略

## 📊 性能监控

### 1. 实时监控
```python
# 监控模拟进度
simulator = HLSimulator(strategy)
simulator.is_verbose = True  # 启用详细日志
results = simulator.run_jobs(stocks)
```

### 2. 结果分析
```python
# 分析模拟结果
analyzer = HistoricLowAnalysis()
latest_dir = analyzer.get_latest_session_dir()
investments = analyzer.load_investment_data(latest_dir)

# 生成性能报告
analyzer.print_blacklist_report(report)
```

### 3. 性能对比
```python
# 对比不同配置的性能
configs = [
    {"amplitude_filter": {"min_amplitude": 0.05}},
    {"amplitude_filter": {"min_amplitude": 0.10}},
    {"amplitude_filter": {"min_amplitude": 0.15}},
]

for config in configs:
    # 运行模拟并分析结果
    pass
```

## 🎯 性能目标

### 1. 基础目标
- **胜率**: > 60%
- **年化收益率**: > 15%
- **最大回撤**: < 20%
- **夏普比率**: > 1.0

### 2. 进阶目标
- **胜率**: > 70%
- **年化收益率**: > 20%
- **最大回撤**: < 15%
- **夏普比率**: > 1.5

### 3. 理想目标
- **胜率**: > 80%
- **年化收益率**: > 25%
- **最大回撤**: < 10%
- **夏普比率**: > 2.0

## 📋 性能报告模板

### 1. 基础报告
```
=== 策略性能报告 ===
模拟期间: 2024-01-01 至 2024-12-31
总投资次数: 1,234
胜率: 68.5%
平均收益率: 12.3%
年化收益率: 18.7%
最大回撤: 15.2%
夏普比率: 1.23
```

### 2. 详细报告
```
=== 详细性能分析 ===

📊 投资分布:
- 1月: 45次投资, 胜率65%, 收益率8.2%
- 2月: 38次投资, 胜率71%, 收益率15.6%
- ...

📈 风险分析:
- 黑名单股票: 51只
- 过滤效果: 振幅过滤减少23%投资机会
- 资金利用率: 78.5%

🎯 优化建议:
- 提高振幅阈值到12%
- 调整斜率阈值到-6度
- 更新黑名单配置
```

## 🔧 性能调优工具

### 1. 参数扫描
```python
def parameter_scan():
    """扫描不同参数组合的性能"""
    amplitude_thresholds = [0.05, 0.10, 0.15, 0.20]
    slope_thresholds = [-3, -5, -7, -10]
    
    best_config = None
    best_performance = 0
    
    for amp in amplitude_thresholds:
        for slope in slope_thresholds:
            # 运行模拟并评估性能
            performance = run_simulation(amp, slope)
            if performance > best_performance:
                best_performance = performance
                best_config = (amp, slope)
    
    return best_config
```

### 2. 回测验证
```python
def backtest_validation():
    """回测验证策略有效性"""
    # 使用历史数据验证策略
    # 分析不同市场环境下的表现
    # 评估策略的稳定性
    pass
```

### 3. 风险分析
```python
def risk_analysis():
    """分析策略风险特征"""
    # 分析最大回撤
    # 评估风险收益比
    # 识别风险来源
    pass
```

## 📞 性能问题排查

### 1. 常见问题
- **胜率过低**: 检查过滤条件是否过于宽松
- **收益率偏低**: 检查止盈止损策略
- **回撤过大**: 检查风险控制机制
- **投资机会过少**: 检查过滤条件是否过于严格

### 2. 排查步骤
1. 检查配置参数是否合理
2. 分析投资分布和结果
3. 对比不同时期的性能
4. 调整参数重新测试

### 3. 优化建议
- 根据市场环境调整参数
- 定期更新黑名单
- 优化过滤条件
- 改进风险管理

## 📚 参考资料

- 策略配置: `CONFIG_GUIDE.md`
- 快速开始: `QUICK_START.md`
- 完整文档: `README.md`
- 配置文件: `strategy_settings.py`
- 分析工具: `strategy_analysis.py`

