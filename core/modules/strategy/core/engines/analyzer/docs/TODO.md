# Analyzer — 架构说明

归因编排在 ``strategy/engines/analyzer``；统计 / ML 原语在 ``modules/analysis``。

边界详见 [docs/BOUNDARY.md](./BOUNDARY.md)。战役口径详见 [ATTRIBUTION_CAMPAIGN.md](../../../../docs/notes/ATTRIBUTION_CAMPAIGN.md)。

---

## 入口

| 场景 | 入口 |
|------|------|
| 库 | ``Analyzer.run(store)``：Prepare → Analyze → Report |
| 终端展示 | ``Analyzer.Presenter.load(output_dir).present(...)`` |

单次 ``simulate`` 不再自动归因。无 CLI ``sa``。战役入口未落地。

---

## 三步流水线

```text
PrepareStep  →  analysis/source.json
AnalyzeStep  →  FactorAnalysisPipeline（stages: univariate / multivariate / run_comparison / ml）
ReportStep   →  summarize → InsightBuilder → analysis/report.json
```

展示：``AnalysisReportPresenter``（``present.py``）。

---

## 目录

```text
analyzer/
├── analyzer.py              # Facade: Analyzer.run()
├── consts.py
├── docs/BOUNDARY.md
└── steps/
    ├── prepare/prepare.py
    ├── analyze/
    │   ├── analyze.py
    │   ├── data/
    │   └── pipeline/
    └── report/
        ├── report.py
        ├── summarize.py
        ├── insight.py
        ├── facts.py
        └── present.py
```
