# 组件：Analyzer（结果分析）

**版本：** `0.2.0`

## 职责

- 在 **价格模拟** 或 **资金模拟** 完成后，按 settings 中 **`analyzer`** 块**可选**执行：
  - **统计报告**（**`StatisticalAnalyzer`**）
  - **机器学习实验**（**`MLAnalyzer`**，目标数据源可指向 enumerator 等）
- 报告写入结果目录下 **`analysis/`** 子树；**失败不影响**模拟器主流程成功状态。

## 主要文件

| 路径 | 说明 |
|------|------|
| `analyzer.py` | **`Analyzer`** / **`AnalyzerConfig`**：解析配置、编排子分析器、写报告 |
| `statistical_analyzer.py` | 指标汇总与表格 |
| `ml_analyzer.py` | 简化 ML 任务入口 |
| `report_builder.py` | 输出格式拼装 |
| `base_analyzer.py` | **`AnalysisContext`** 等共用类型 |

## 配置

- 由策略 **`settings["analyzer"]`** 控制 `enabled`、`statistical`、`ml` 子块（详见 **`AnalyzerConfig.from_raw_settings`**）。
