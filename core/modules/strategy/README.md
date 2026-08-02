# Strategy Module

策略执行：把用户钩子经 BacktestEngine ``RunCallbacks`` 挂入回测，并做 jobs / 报告等周边。

**架构硬约束**见 [`BOUNDARY_NOTES.md`](BOUNDARY_NOTES.md)「与 BacktestEngine 的关系」——枚举器仅 *JobBuilder + *JobExecutor；勿加 TimelineBuilder / 平行 session。

## 三层结构（示意；细节以代码与 BOUNDARY_NOTES 为准）

```
core/
├── helpers/                 # 纯工具（无业务编排、无 mode 分支）
│   ├── statistics.py
│   ├── calendar.py
│   ├── opportunity_csv.py
│   └── stock_meta.py
│
├── services/                # 业务服务
│   ├── discovery/           # DiscoveryService（facade 唯一 export）
│   ├── settings/
│   └── data/                # 数据加载、参数/路径解析、输出持久化
│       ├── strategy_data_config.py
│       ├── entity_data.py
│       ├── params_resolver.py
│       ├── output_paths.py
│       └── output_recorder.py
│
├── hooks/                   # 用户策略契约
│   └── context/data_context.py   # StrategyContext（hook 数据视图）
│
└── engines/enumerator/      # 主逻辑（编排 + 计算）
    ├── engine.py            # 薄路由：preprocess → mode pipeline → postprocess
    ├── shared/              # 跨模式共享
    │   ├── runtime.py       # RuntimeContext / RuntimeStatus / EnumeratorRuntime
    │   ├── fingerprint.py
    │   └── report/statistics.py
    ├── entity_based/        # 逐股 timeline（见 entity_based/README.md）
    └── slice_based/         # 日历切片（见 slice_based/README.md）
```

## 流程

```
Strategy.enumerate()
  → services: discovery / settings / params_resolver / output_paths
  → enumerator/engine.py
       → shared: fingerprint + GlobalDataPreloader
       → entity_based/pipeline  |  slice_based/pipeline
       → shared/report + services/data/output_recorder
```

## Context（三种）

| Context | 用户 hook | 机器 runtime | 运行状态 |
|---------|-----------|--------------|----------|
| 位置 | `hooks/hook_params/strategy_context.py` | `enumerator/common/runtime.py` + 各模式 `context/runtime.py` | 各模式 `context/status.py` |
| 组装 | 各模式 `context/data.py` | engine 构建 RuntimeContext | pipeline 更新 RuntimeStatus |

## 用户策略 import（公开面）

策略作者与 extensions **只**从以下路径 import，勿使用 `core.engines.*` 内部路径：

```python
from core.modules.strategy.contracts import (
    CalendarAsOfResult,
    StrategyContext,
    Opportunity,
    StrategyHooks,
)
```

`Strategy` facade 亦可在包根 import：

```python
from core.modules.strategy import Strategy
from core.modules.strategy.contracts import StrategyContext, Opportunity, StrategyHooks
```

`core.hooks.*` 为模块内部路径，用户策略勿直接 import。

## settings.data 声明

见各模式 README；字段 **`data_key`** + **`base` / `required`**（breaking，无旧字段）。

---

**Requires**: core>=0.5.0
