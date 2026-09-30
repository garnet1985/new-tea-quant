# Analyzer vs modules.analysis — boundary

## modules.analysis（纯统计 / ML，无业务、无 I/O）

- table / column in → struct out
- **入口**：``Analysis.Classical.*``、``Analysis.ML.*``
- **位置**：``core/modules/analysis/``

## strategy/engines/analyzer（业务编排 + 叙事）

| 包 | 职责 |
|----|------|
| ``analyzer.py`` | Facade / API 暴露 |
| ``pipeline.py`` | 战役编排（``AttributionPipeline`` 只串步骤） |
| ``steps/campaign/`` | attribution 配置 / overlay / 展开 / 查缓存 / 钉住 / 拼表 / 相对基准贡献度 / 总结 / 落盘 / 展示 |
| ``steps/prepare/`` | 回测产物 → ``source.json``（编排；I/O 走 ``ArtifactStore``） |
| ``steps/analyze/`` | 读 source → 因素分析 pipeline → ``AnalyzeOutput`` |
| ``steps/report/`` | summarize + insight + persist ``report.json``；``present.py`` 终端展示 |

Analyzer 担任归因职责。单次回测顺带归因已去掉；战役（matrix、group、``results/attribution/``）口径见 [ATTRIBUTION_CAMPAIGN.md](../../../../docs/notes/ATTRIBUTION_CAMPAIGN.md)。``Analyzer.run`` 仍是单 version 库入口；``Analyzer.campaign`` 走 ``AttributionPipeline``；``Analyzer.rolling`` 走 ``RollingPipeline``；``Analyzer.run`` 是单 version 机会表切片。

### Report 步结构

```text
report.py              # 入口：总结 → insight → 持久化
summarize.py           # 总结：整理 analyze 结果为 report 主体
insight.py             # CLI 叙事（InsightBuilder）
facts.py               # 结构化 facts（无 CLI 文案）
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

## 入口（当前）

```text
Analyzer.run(store)      → PrepareStep → AnalyzeStep → ReportStep
Analyzer.campaign(key)   → AttributionPipeline → steps/campaign/
Analyzer.rolling(key)    → RollingPipeline → steps/rolling/
```

``Strategy.simulate`` **不再**调用 Analyzer。战役报告写在 ``results/attribution/{n}/parameter/``，滚动写 ``rolling/``。命中/补跑的 version 钉住。平时 Run 把 version 记进 ``group_meta``。CLI ``sa`` / ``sz`` / ``sw``。

## 依赖方向

```text
Analyzer.campaign / Analyzer.rolling / Analyzer.run → AttributionPipeline / RollingPipeline / 单 version 三步 → modules.analysis
```

``modules.analysis`` 禁止 import strategy。
