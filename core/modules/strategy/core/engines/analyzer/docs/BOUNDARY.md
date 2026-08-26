# Analyzer vs modules.analysis — boundary

## modules.analysis（纯统计 / ML，无业务、无 I/O）

- table / column in → struct out
- **入口**：``Analysis.Classical.*``、``Analysis.ML.*``
- **位置**：``core/modules/analysis/``

## strategy/engines/analyzer（业务编排 + 叙事）

| 包 | 职责 |
|----|------|
| ``analyzer.py`` | Facade / API 暴露 |
| ``pipeline/`` | Prepare → Analyze → Report |
| ``steps/prepare/`` | 回测产物 → ``source.json`` |
| ``steps/analyze/`` | 读 ``source.json``；决定空间；attribution |
| ``steps/report/`` | 叙事 + insights + 写 ``report.json`` |
| ``support/`` | 路径、step 映射、outcome 配置 |
| ``io/`` | BFF/UI payload |

### Analyze 步内部分工

| 留在 analyze step（业务） | 在 modules.analysis（可复用） |
|---------------------------|-------------------------------|
| ``DecisionSpaceBuilder``、``CaptureDataset``、attribution stages | ``ColumnProfiler``、分桶、相关、回归、XGB |

## Pipeline（3 步）

```text
PrepareStep.run(store)     → source.json
AnalyzeStep.run(path)      → AnalyzeOutput（内存）
ReportStep.run(store, …)   → report.json
```

## 依赖方向

```text
BFF / CLI → Strategy → Analyzer → modules.analysis
```

``modules.analysis`` 禁止 import strategy。
