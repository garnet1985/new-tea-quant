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
| 读 facts / insights | `Strategy.step_analysis_from_output_dir` / `Strategy.resolve_step_analysis` |
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
        ├── facts.py
        └── present.py
```

---

## 工作台归因报告

约定：

- 枚举 / 价格 / 资金 **三个报告 Tab 各自展示该步归因**；`analysis.enabled` 时默认出现（不另开 Tab、不默认折叠）。
- **FED 只读结构化内容**；标题、说明、空态、样式在 FED。CLI `sa` 继续用 `InsightBuilder` + `present.py`，不和 UI 共用叙事。
- **进度不新增 step / weight**：归因并进现有 `report` 步（「生成报告」覆盖写 overall + 归因）。

### 1. Progress：归因并进 `report` — **done**

- 三层 Pipeline：`enter_step("report")` → 写 overall/entity_list → **不** `complete_step("report")`
- `Strategy._run_steps`：Pipeline 返回后跑 `_maybe_run_analysis`，再 `complete_step_bound("report")`（disable 时也 complete）
- 不改 `_STEPS` / `_STEP_WEIGHTS`

### 2. BFF 读模型 — **done**

- `GET .../report/:step/:version` 的 `analysis` 含 `enabled`（该 version 快照 `settings.analysis.enabled`，默认 false）
- UI 用 **facts**（`available`、`field_key`、`tiers`、相关/status、skip 计数等）；不下发 CLI 中文 `headline` / `next_steps` / `chart_note`
- `InsightBuilder` 仍写入 `report.json` 供 CLI `sa`；Python `load_payload` 同时带 `insights`，BFF 只把 `facts` 给 FED

### 3. FED 报告面板 — **done**

- 有 `enabled` 且该 Tab `done`：**默认渲染**该步归因区块（挂在 Tab 内容下方）
- `enabled=false`：**整块不渲染**（不拉 V2-07、无「尚未生成」占位）
- 三层共用 `StepAnalysisInsights`，数据按 `enum` / `price` / `portfolio` 分拉
- 区块标题、分档说明、空态、错误文案在 `reportSectionMeta`
- 本轮不做设置面板开关；对比弹窗不带归因

### 4. 回归 — **done**

- progress：enable / disable 两条路径，report 步 complete 时机（见 `test_analysis_progress.py`）
- BFF：`analysis.enabled` + `available` + `facts`（见 `test_step_report.py` / `test_ui_facts.py`）
- FED：enable 默认可见、disable 不占位

---

## 后续（非阻塞）

- ML stage：依赖 xgboost 时装配；无依赖时 skipped
- 因子研究（IC / 滚动 / 全市场）→ 未来 `factor` 模块，不在本 pipeline
