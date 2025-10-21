# RTB策略机器学习模块

这个目录包含RTB策略的机器学习相关脚本和工具。

## 文件说明

### 核心分析脚本

- **`analyze_rtb_trading_results.py`** - 分析RTB策略的交易结果
  - 提取成功和失败案例的特征
  - 进行机器学习分析和特征重要性评估
  - 生成可视化图表

- **`compare_rtb_vs_script_reversals.py`** - 对比RTB策略和脚本识别的反转点
  - 分析哪些反转点被RTB策略过滤掉
  - 找出RTB策略错过的投资机会

- **`simple_rtb_condition_optimization.py`** - 简化版RTB条件优化
  - 基于脚本识别的反转点数量
  - 提供RTB策略筛选条件的调整建议

- **`optimize_rtb_conditions_for_script_reversals.py`** - 详细版RTB条件优化
  - 深度分析脚本识别的反转点特征
  - 提供更精细的参数调整建议

### 使用方法

#### 方法1：使用快速启动工具（推荐）
```bash
# 在项目根目录运行
python rtb_quick_start.py analyze      # 分析交易结果
python rtb_quick_start.py compare      # 对比反转点
python rtb_quick_start.py optimize     # 优化条件
python rtb_quick_start.py simulate     # 运行模拟
```

#### 方法2：直接运行脚本
```bash
# 在项目根目录运行
python app/analyzer/strategy/RTB/ml/analyze_rtb_trading_results.py
python app/analyzer/strategy/RTB/ml/compare_rtb_vs_script_reversals.py
python app/analyzer/strategy/RTB/ml/simple_rtb_condition_optimization.py
```

## 工作流程

1. **运行策略模拟** → 生成交易结果数据
2. **分析交易结果** → 了解策略表现和特征重要性
3. **对比反转点** → 找出错过的投资机会
4. **优化条件** → 调整策略参数以增加投资机会
5. **重新运行模拟** → 验证优化效果

## 输出文件

- `rtb_ml_enhanced_analysis.png` - 交易结果分析图表
- 控制台输出包含详细的分析结果和建议

## 注意事项

- 确保在项目根目录运行脚本
- 需要先运行策略模拟生成数据才能进行分析
- 分析结果会显示在控制台中
