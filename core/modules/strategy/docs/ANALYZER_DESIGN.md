#!/usr/bin/env python3
# Analyzer 模块设计文档

## 概述

Analyzer 是 Strategy 模块的“分析层”，负责在 **枚举器 / 模拟器** 生成结果之后，
基于这些结果做进一步的统计学与机器学习分析，输出独立的分析报告。

本设计只针对本次重构范围内的两类分析器：

- **StatisticalAnalyzer**：统计学分析器，提供胜率 / 盈利分布、按时间维度的表现等描述性统计。
- **MLAnalyzer**：机器学习分析器，基于 XGBoost 对“枚举器机会结果”做因子重要性分析。

设计原则：

- **只读结果**：Analyzer 只读取枚举器 / 模拟器产出的结果文件，不修改原始结果。
- **可选附加步骤**：通过 settings 中的布尔开关控制，默认关闭，需要时在回测后“顺便跑一下”。
- **模板化实现**：统计学分析的“可选指标”由框架提供模板，用户只在 settings 中选择要启用的指标，不写代码。
- **简单可展示**：MLAnalyzer 第一版只针对“枚举器机会结果 + XGBoost 特征重要性”，作为开源项目的“广告位”，不做复杂 AutoML。

---

## 文件结构

```text
app/core/modules/strategy/components/analyzer/
  - analyzer.py             # 统一入口 / 调度器（对外只暴露 Analyzer.run）
  - base_analyzer.py        # 抽象基类，约定输入 / 输出接口
  - statistical_analyzer.py # 统计学分析实现（StatisticalAnalyzer）
  - ml_analyzer.py          # 机器学习分析实现（MLAnalyzer, 使用 XGBoost）
  - report_builder.py       # 报告组装与序列化（JSON / Markdown）
```

结果输出目录（示例，以 PriceFactorSimulator 为例）：

```text
app/userspace/strategies/{strategy_name}/results/
  └── simulations/
      └── price_factor/{sim_version}/
          ├── 0_session_summary.json
          ├── metadata.json
          ├── {stock_id}.json
          └── analysis/                     # ← 新增的 Analyzer 输出目录
              ├── statistical_report.json
              ├── statistical_report.md
              ├── ml_factor_importance.json
              └── ml_factor_importance.md
```

对于只基于枚举器（不跑模拟器）场景，可以在 **枚举结果版本目录** 下建立相同的 `analysis/` 子目录，
命名规则保持一致（由 `ResultPathManager` 或未来的 `AnalysisPathManager` 统一管理）。

---

## Settings 设计

在现有 `StrategySettings` 基础上扩展一个 `analyzer` 小节，例如：

```python
"analyzer": {
    "enabled": True,          # 总开关
    "statistical": {
        "enabled": True,
        "metrics": [
            "win_rate_distribution",
            "pnl_distribution",
            "monthly_performance",
            "yearly_performance",
            "max_drawdown",
        ]
    },
    "ml": {
        "enabled": False,
        "target": "enumerator",    # 第一版固定为 "enumerator"
        "task": "classification",  # 第一版固定为 win/loss 二分类
    },
}
```

说明：

- 用户 **只能选择 metrics 的 key**，实现由框架内置，不开放自定义统计公式。
- MLAnalyzer 第一版只支持：
  - `target = "enumerator"`：基于枚举器的机会结果做因子重要性分析；
  - `task = "classification"`：预测机会 win/loss（二分类），输出特征重要性。

对应的 Settings dataclass 计划：

- `AnalyzerSettings`：挂在 `StrategySettings` 下，负责：
  - `enabled` 总开关解析；
  - `StatisticalAnalyzerSettings` 与 `MLAnalyzerSettings` 的子对象构建与校验；
  - 合法性校验（metrics 值是否在内置列表中、target 是否支持等）。

---

## 与现有流水线的集成

### 1. 与模拟器的集成（首要场景）

在 PriceFactorSimulator / CapitalAllocationSimulator 完成核心计算并将结果落盘之后，
根据 settings 决定是否调用 Analyzer：

```python
if strategy_settings.analyzer.enabled:
    Analyzer.run(
        strategy_name=strategy_name,
        sim_type="price_factor",  # 或 "capital_allocation"
        sim_version_dir=sim_version_dir,
        settings=strategy_settings.analyzer,
        data_manager=data_manager,  # 如有必要，可选参数
    )
```

设计要点：

- Analyzer 不参与模拟器内部逻辑，只在“收尾阶段”运行。
- 调用失败（例如 XGBoost 未安装）不得影响模拟器主流程：
  - 记录 warning 日志；
  - 跳过该分析器，继续返回模拟结果。

### 2. 与枚举器的集成（后续可选）

MLAnalyzer 第一版目标是“只针对枚举器的机会结果分析因子重要性”，
但为了保持设计完整性，这里预留接口：

- 在枚举器完成一次完整枚举（并将 `*_opportunities.csv` / `*_targets.csv` 落盘）后，
  可以在对应版本目录下调用：

```python
if strategy_settings.analyzer.ml.enabled and strategy_settings.analyzer.ml.target == "enumerator":
    Analyzer.run_for_enumerator(
        strategy_name=strategy_name,
        enum_version_dir=enum_version_dir,
        settings=strategy_settings.analyzer,
        data_manager=data_manager,
    )
```

第一版可以只实现基于 **模拟器结果路径** 的入口（即由模拟器触发 MLAnalyzer），
后续如有需要再开放“只基于枚举器版本跑 ML 分析”的入口。

---

## StatisticalAnalyzer 设计

### 1. 可用 metrics 列表（白名单）

为了避免魔法字符串失控，统计学分析的指标在代码中定义为一个枚举类，
settings 中的 `metrics` 列表只能从该枚举的值中选择。

建议的枚举定义（示意）：

```python
from enum import Enum


class StatisticalMetric(str, Enum):
    WIN_RATE_DISTRIBUTION = "win_rate_distribution"
    PNL_DISTRIBUTION = "pnl_distribution"
    MONTHLY_PERFORMANCE = "monthly_performance"
    YEARLY_PERFORMANCE = "yearly_performance"
    MAX_DRAWDOWN = "max_drawdown"
    HOLDING_PERIOD_BUCKET = "holding_period_bucket"
```

各指标含义：

- **win_rate_distribution**：按单笔投资 ROI 分桶（例如 \[-100%, -50%), \[-50%, 0), \[0, 10%), ...），统计每个桶的胜率与样本数。
- **pnl_distribution**：单笔盈亏（PnL 或 ROI）的分布直方图数据（用于画 histogram）。
- **monthly_performance**：按月统计收益率、胜率、交易次数等。
- **yearly_performance**：按年统计收益率、胜率、最大回撤等。
- **max_drawdown**：全周期最大回撤及对应起止时间。
- **holding_period_bucket**：按持仓天数（holding period）分桶，统计各桶的平均 ROI 与胜率。

后续如果需要，可以追加更多 metrics（例如：`weekday_effect`, `top_gain_loss` 等），
但必须通过扩展 `StatisticalMetric` 枚举来完成。

### 2. Settings 解析与校验

- 用户在 settings 中配置的是字符串，例如：

  ```python
  "metrics": ["win_rate_distribution", "monthly_performance"]
  ```

- 在 `StatisticalAnalyzerSettings` 中：
  - 将字符串映射到 `StatisticalMetric`，非法值在校验阶段报错或记录 WARNING；
  - 内部统一使用 `StatisticalMetric` 枚举，避免魔法字符串散落在实现代码中。

### 3. 实现轮廓

```python
class StatisticalAnalyzer(BaseAnalyzer):
    def __init__(self, settings: StatisticalAnalyzerSettings, context: AnalysisContext):
        ...

    def run(self) -> dict[str, Any]:
        report: dict[str, Any] = {}
        for metric in self.settings.metrics:  # List[StatisticalMetric]
            if metric is StatisticalMetric.WIN_RATE_DISTRIBUTION:
                report["win_rate_distribution"] = self._calc_win_rate_distribution()
            elif metric is StatisticalMetric.PNL_DISTRIBUTION:
                report["pnl_distribution"] = self._calc_pnl_distribution()
            # ...
        return report
```

内部实现优先使用 `pandas + numpy`：

- `pandas.DataFrame`：承载投资记录 / 机会记录；
- `groupby` / `resample("M")` / `resample("Y")`：实现按月 / 按年统计；
- `numpy.histogram` 或 `pandas.cut`：实现 ROI / PnL 分桶。

---

## MLAnalyzer 设计（XGBoost）

### 1. 目标与范围

- **目标**：基于“枚举器的机会结果”分析因子（包括 extra fields）的重要性，
  输出一份按重要性排序的因子列表，作为开源项目的“卖点”。
- **范围限制**：
  - 仅使用枚举器的 `*_opportunities.csv` 作为特征来源；
  - 第一版只做 **二分类任务**：预测机会是否“成功/失败”（win/loss）；
  - 使用 **XGBoost** 作为唯一模型，不做复杂 AutoML / 参数搜索。

### 2. 输入数据

**特征来源**：

- 枚举器机会表中的所有数值型/可数值化字段，包括：
  - 基础字段：`trigger_price`, `stop_loss_price`, `take_profit_price`, `holding_days`, ...
  - extra fields：用户在枚举阶段附加的任意数值字段（例如信号强度、打分等）。

**标签（label）来源**：

- 理想情况：机会记录中已经有表示结果的字段，例如：
  - `is_win`（布尔/0-1），或
  - `exit_roi`（>0 视为 win，<=0 视为 loss）。
- 如果当前没有结果字段，后续可以：
  - 在枚举阶段增加一个极简的 `outcome` 字段，或
  - 联合 PriceFactorSimulator 结果补写 win/loss（本设计不在此展开，先假设有可用 label）。

### 3. 模型与依赖

- 使用 **XGBoost**：
  - 优点：对特征缩放不敏感，天然支持特征重要性（gain/weight/cover）。
  - 依赖：项目 `requirements.txt` 中已经存在 XGBoost（如无，则后续补充）。
- 任务类型：
  - 固定为二分类（classification），预测 win/loss。

### 4. 输出格式

MLAnalyzer 主要输出一份“因子重要性榜单”：

```json
{
  "model": "xgboost",
  "task": "classification",
  "n_samples": 12345,
  "n_features": 20,
  "feature_importance": [
    {"name": "signal_strength", "importance": 0.35, "rank": 1},
    {"name": "trigger_price", "importance": 0.20, "rank": 2},
    {"name": "holding_days", "importance": 0.10, "rank": 3}
  ]
}
```

并由 `report_builder` 生成一个简短的 Markdown 概览，例如：

- Top 10 因子及其重要性；
- 简单的自然语言摘要（如：“信号强度是当前模型中最重要的因子，其次是触发价格和持仓天数”）。

### 5. 实现轮廓

```python
class MLAnalyzer(BaseAnalyzer):
    def __init__(self, settings: MLAnalyzerSettings, context: AnalysisContext):
        ...

    def run(self) -> dict[str, Any]:
        # 1. 加载枚举结果（opportunities）
        # 2. 构造特征矩阵 X 与标签 y
        # 3. 训练 XGBoost 模型
        # 4. 提取并排序特征重要性
        # 5. 返回标准化的 report dict
        ...
```

若 XGBoost 未安装或训练失败：

- 记录 warning 日志；
- 返回一个包含错误信息的 report（例如 `{ "error": "xgboost_not_available" }`），
  但不影响主流程。

---

## BaseAnalyzer 与报告生成

### 1. BaseAnalyzer 抽象

```python
class BaseAnalyzer(ABC):
    def __init__(self, context: AnalysisContext):
        self.context = context

    @abstractmethod
    def run(self) -> dict[str, Any]:
        """执行分析并返回结构化报告（Python dict）"""
        raise NotImplementedError
```

`AnalysisContext` 负责封装运行所需的环境信息，例如：

- `strategy_name`
- `sim_type` / `enum_or_sim_version_dir`
- `data_manager`（如需要 DB 访问）

### 2. report_builder

统一负责：

- 将各 Analyzer 返回的 **dict 报告** 序列化为 JSON 文件；
- 生成简短的 Markdown 概览（可选）。

这样可以保持 Analyzer 只关注“算出什么”，而不关心“写到哪里 / 用什么格式”。

---

## 小结

- **StatisticalAnalyzer**：
  - 使用 `StatisticalMetric` 枚举管理所有可用指标；
  - 用户在 settings 中通过字符串选择指标，内部转换为枚举；
  - 依赖 `pandas + numpy` 实现各类描述性统计。
- **MLAnalyzer**：
  - 只针对“枚举器机会结果”，使用 XGBoost 做二分类；
  - 输出标准化的因子重要性报告（JSON + Markdown）；
  - XGBoost 缺失时只记录 warning，不影响主流程。

后续实现将严格按照本设计文档，在 `components/analyzer/` 目录下补全代码结构。

