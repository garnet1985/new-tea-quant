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
| ``steps/layer/`` | 层内诊断库（事实 / 结论 / 建议）；不挂在 simulate / CLI |
| ``steps/prepare/`` | 回测产物 → ``source.json``（编排；I/O 走 ``ArtifactStore``） |
| ``steps/analyze/`` | 读 source → 因素分析 pipeline → ``AnalyzeOutput`` |
| ``steps/report/`` | summarize + insight + persist ``report.json``；``present.py`` 终端展示 |

Analyzer 担任归因职责。公开入口按层：``attribute_enumerate`` / ``attribute_price`` / ``attribute_portfolio``（CLI ``sea`` / ``spa`` / ``soa``）。须已有主 version；对照格写副本 ``{vid}-{r}``。战役口径见 [ATTRIBUTION_CAMPAIGN.md](../../../../docs/notes/ATTRIBUTION_CAMPAIGN.md)。``Analyzer.run`` 仅战役内部切片（如 spa trades），无 CLI。``Analyzer.rolling`` 走 ``RollingPipeline``。

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
Analyzer.attribute_*(key) → AttributionPipeline(kind=…) → steps/campaign/
Analyzer.rolling(key)     → RollingPipeline → steps/rolling/
Analyzer.run(store)       → PrepareStep → AnalyzeStep → ReportStep（战役内部）
LayerPipeline.run(store)  → 层内诊断库（无公开 CLI）
```

``Strategy.simulate`` 只回测，不归因。战役报告写在 ``results/attribution/{n}/{enumerate|price_factor|portfolio}/``，滚动写 ``rolling/``。CLI ``sea`` / ``spa`` / ``soa`` / ``sw``。

## 依赖方向

```text
Analyzer.attribute_* / Analyzer.rolling / Analyzer.run → 各 pipeline → modules.analysis（切片 / 战役才用）
```

``modules.analysis`` 禁止 import strategy。
