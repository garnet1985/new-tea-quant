# Analyzer — 架构说明（已完成）

回测闭环最后一环：**解释这一次 version、这一层 step** 的 inputs 与 outputs 如何共变。

- **编排与产物**：`strategy/engines/analyzer`
- **统计 / ML 原语**：`modules/analysis`（无业务、无 I/O）

边界详见 [docs/BOUNDARY.md](./docs/BOUNDARY.md)。

---

## 入口

| 场景 | 入口 |
|------|------|
| 自动生成 | `Strategy.simulate` →（`settings.analysis.enabled`）→ `Analyzer.run` |
| 读 insights | `Strategy.step_analysis_from_output_dir` / `Strategy.resolve_step_analysis` |
| 终端展示 | `Strategy.present_analysis_report`（CLI `sa`，只读已有 report） |

无独立 `Strategy.analyze`；analyze 内嵌于 simulate 主步。

---

## 三步流水线

```text
PrepareStep  →  analysis/source.json
AnalyzeStep  →  FactorAnalysisPipeline（stages: univariate / multivariate / run_comparison / ml）
ReportStep   →  summarize → InsightBuilder → analysis/report.json
```

展示：`AnalysisReportPresenter`（`present.py`）。

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
        └── present.py
```

---

## 后续（非阻塞）

- ML stage：依赖 xgboost 时装配；无依赖时 skipped
- 因子研究（IC / 滚动 / 全市场）→ 未来 `factor` 模块，不在本 pipeline
