# RTB策略快速启动指南

## 🚀 快速开始

使用快速启动工具进行RTB策略分析和优化：

```bash
# 查看所有可用命令
python rtb_quick_start.py help

# 运行RTB策略模拟
python rtb_quick_start.py simulate

# 分析交易结果
python rtb_quick_start.py analyze

# 对比反转点识别
python rtb_quick_start.py compare

# 优化策略条件
python rtb_quick_start.py optimize
```

## 📁 文件结构

```
RTB策略相关文件:
├── rtb_quick_start.py                    # 🎯 快速启动入口文件
├── start.py                              # 主程序入口
└── app/analyzer/strategy/RTB/
    ├── RTB.py                           # RTB策略核心代码
    ├── settings.py                      # 策略配置参数
    ├── ml/                              # 机器学习分析模块
    │   ├── analyze_rtb_trading_results.py      # 交易结果分析
    │   ├── compare_rtb_vs_script_reversals.py  # 反转点对比
    │   ├── simple_rtb_condition_optimization.py # 条件优化
    │   └── README.md                    # ML模块说明
    ├── feature_identity/                # 特征识别模块
    │   ├── reversal_data_generator_enhanced.py
    │   └── reversal_identify.py
    └── tmp/                             # 模拟结果输出目录
```

## 🔧 常用工作流程

### 1. 运行策略模拟
```bash
python rtb_quick_start.py simulate
```
- 运行RTB策略回测
- 生成交易结果数据到 `tmp/` 目录

### 2. 分析交易结果
```bash
python rtb_quick_start.py analyze
```
- 分析成功/失败案例的特征
- 进行机器学习分析
- 生成特征重要性报告

### 3. 对比反转点识别
```bash
python rtb_quick_start.py compare
```
- 对比RTB策略和脚本识别的反转点
- 找出被过滤的投资机会

### 4. 优化策略条件
```bash
python rtb_quick_start.py optimize
```
- 基于分析结果优化筛选条件
- 提供参数调整建议

## 📊 当前策略表现 (V25.0_Script_Optimized)

- **总投资次数**: 5,263
- **胜率**: 47.4%
- **平均ROI**: 5.0%
- **年化收益率**: 15.5%
- **平均每只股票投资次数**: 10.53

## 🎯 策略特点

- **多层次反转识别**: 月线识别大趋势，周线精确定位
- **机器学习增强**: 基于历史数据优化参数
- **动态止损止盈**: 分阶段获利了结
- **风险控制**: 市值、估值等多维度筛选

## 📈 优化历程

- V21.0: 基础ML增强版本
- V22.0: 第一次参数优化
- V23.0: 平衡收益与机会
- V24.0: 扩大投资机会
- V25.0: 基于脚本分析优化 (当前版本)

## 🔍 技术特性

- **分层识别算法**: 月线→周线→日线的多层次反转点识别
- **特征工程**: 22个技术指标和基本面指标
- **机器学习**: Random Forest, Gradient Boosting, Logistic Regression
- **动态参数**: 基于历史表现自适应调整阈值

## 📝 注意事项

1. 确保在项目根目录运行所有命令
2. 先运行模拟生成数据，再进行其他分析
3. 分析结果会显示在控制台并保存图表
4. 策略参数会根据分析结果自动优化
