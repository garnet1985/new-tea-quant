# ROI 统一标准

## 基本原则

在整个系统中，ROI（投资回报率）遵循以下统一标准：

### 1. 内部存储格式：小数（Decimal）
- **格式**: 0.20 表示 20%
- **精度**: 4 位小数（避免小 ROI 被舍入为 0）
- **范围**: -1.0 到正无穷（-100% 到无限）

### 2. 显示格式：百分比（Percentage）
- **格式**: 20% 或 20.5%
- **转换**: `roi_decimal * 100`
- **精度**: 通常显示 1-2 位小数

## 代码示例

### ✅ 正确用法

```python
# 1. 计算和存储 - 使用小数格式，4 位精度
investment['overall_profit_rate'] = AnalyzerService.to_ratio(
    overall_profit, 
    purchase_price, 
    decimals=4  # 0.0026 = 0.26%
)

# 2. 比较判断 - 使用小数格式
if inv['overall_profit_rate'] >= 0.2:  # 20%
    profitable_count += 1
elif inv['overall_profit_rate'] >= 0:  # 0%
    minor_profitable_count += 1

# 3. 显示输出 - 转换为百分比
avg_roi = session_summary.get('avg_roi', 0) * 100.0
print(f"平均ROI: {avg_roi:.1f}%")  # 输出: "平均ROI: 0.3%"

# 4. 日志输出 - 转换为百分比
logger.info(f"ROI: {roi * 100:.2f}%")  # 输出: "ROI: 0.26%"
```

### ❌ 错误用法

```python
# 错误 1: 存储时使用百分比格式
investment['overall_profit_rate'] = (profit / purchase_price) * 100  # ❌

# 错误 2: 比较时使用百分比
if inv['overall_profit_rate'] >= 20:  # ❌ 应该用 0.2
    profitable_count += 1

# 错误 3: 精度不足导致小 ROI 丢失
roi = AnalyzerService.to_ratio(profit, purchase_price, decimals=2)  # ❌
# 0.003 会被舍入为 0.00

# 错误 4: 显示时重复转换
avg_roi = session_summary.get('avg_roi', 0)  # 已经是小数
print(f"平均ROI: {avg_roi}%")  # ❌ 会显示 "0.003%" 而不是 "0.3%"
```

## 关键文件

### 1. SimulatingService (投资结算)
- **文件**: `app/analyzer/components/simulator/services/simulating_service.py`
- **行号**: 430-431
- **作用**: 计算并存储单个投资的 ROI（小数格式，4 位精度）

### 2. PostprocessService (汇总统计)
- **文件**: `app/analyzer/components/simulator/services/postprocess_service.py`
- **行号**: 
  - 61-69: 累加 ROI（小数格式）
  - 103-108: 股票级别平均 ROI（小数格式，4 位精度）
  - 214-215: 会话级别平均 ROI（小数格式，4 位精度）
  - 284: 显示时转换为百分比

### 3. BaseStrategy (分析报告)
- **文件**: `app/analyzer/components/base_strategy.py`
- **行号**: 800, 842
- **作用**: 从模拟结果提取 ROI 用于分析（转换为百分比）

## 数据流

```
投资结算 (小数, 4位)
    ↓
单股汇总 (小数, 4位)
    ↓
会话汇总 (小数, 4位)
    ↓
显示报告 (百分比, 1-2位)
```

## 为什么使用 4 位小数？

对于小 ROI 值：
- `0.003` (0.3%) → `round(0.003, 2)` = `0.00` ❌
- `0.003` (0.3%) → `round(0.003, 4)` = `0.0030` ✅

示例：
- RTB 策略平均 ROI = 0.29 / 113 = 0.00257 (0.257%)
- 2 位精度: 0.00 → 显示为 0.0% ❌
- 4 位精度: 0.0026 → 显示为 0.3% ✅

## 测试检查清单

在修改 ROI 相关代码时，检查：

- [ ] 存储时使用小数格式
- [ ] 使用 4 位精度（`decimals=4`）
- [ ] 比较时使用小数值（0.2 不是 20）
- [ ] 显示时乘以 100 转换为百分比
- [ ] 日志输出使用百分比格式
- [ ] 不要重复转换（避免 0.003% 的错误显示）

## 相关工具函数

```python
# 计算比率（小数格式）
AnalyzerService.to_ratio(numerator, denominator, decimals=4)

# 计算百分比（已经是百分比格式，不常用于 ROI）
AnalyzerService.to_percent(numerator, denominator, decimals=2)

# 计算年化收益率（接受小数格式的 ROI）
AnalyzerService.get_annual_return(roi_decimal, duration_days)
```
