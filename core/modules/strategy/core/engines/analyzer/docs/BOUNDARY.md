# Analyzer vs modules.analysis — boundary

## modules.analysis（纯统计 / ML，无业务、无 I/O）

- table / column in → struct out
- **入口**：``Analysis.Classical.*``、``Analysis.ML.*``
- **位置**：``core/modules/analysis/``

## strategy/engines/analyzer（业务编排 + 叙事）

| 包 | 职责 |
|----|------|
| ``analyzer.py`` | Facade / API 暴露 |
| ``steps/prepare/`` | 回测产物 → ``source.json``（编排；I/O 走 ``ArtifactStore``） |
| ``steps/analyze/`` | 读 source → 因素分析 pipeline → ``AnalyzeOutput`` |
| ``steps/report/`` | summarize + insight + persist ``report.json``；``present.py`` 终端展示 |

### Report 步结构

```text
report.py              # 入口：总结 → insight → 持久化
summarize.py           # 总结：整理 analyze 结果为 report 主体
insight.py             # 下结论（InsightBuilder）
present.py             # 终端展示
```

### Analyze 步结构

```text
analyze.py              # 入口：读 source → 调 pipeline
data/                   # strategy 侧：为 analysis 模块准备输入
  decision_space.py     # 决定空间
  capture_dataset.py    # source.json → 数值序列 / 特征矩阵
  outcome.py            # enum/price/portfolio 的 ROI / win 字段映射
pipeline/
  pipeline.py           # FactorAnalysisPipeline：遍历 stages，收集结果
  context.py            # StageInput + AnalysisStage 协议
  stages/               # 各因素分析成员（加新分析 = 加 stage + 注册 DEFAULT_STAGES）
    univariate.py       # 单因素
    multivariate.py     # 多因素
    run_comparison.py   # 对比
    ml.py               # ML
```

| 留在 analyze step（strategy） | 在 modules.analysis（可复用） |
|-------------------------------|-------------------------------|
| ``DecisionSpaceBuilder``、``CaptureDataset``、stages | 分桶、相关、回归、XGB |

## Pipeline（simulate 内嵌 analyze）

```text
Strategy.simulate → BackTestPipeline.run → (若 analysis.enabled) Analyzer.run
PrepareStep → AnalyzeStep → ReportStep
```

``settings.analysis.enabled=false`` 时不跑 analyze 步。

## 依赖方向

```text
BFF / CLI → Strategy → Analyzer → modules.analysis
```

``modules.analysis`` 禁止 import strategy。
