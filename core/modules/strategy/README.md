# Strategy Module (v0.6.0)

策略执行模块。枚举入口：`Strategy.enumerate()` → `EnumeratorEngine`（薄路由）→ `entity_based` / `slice_based`。

## 三层结构

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
│   └── context/data_context.py   # DataContext（hook 数据视图）
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
| 位置 | `hooks/data_context.py` | `enumerator/shared/runtime.py` + 各模式 `context/runtime.py` | 各模式 `context/status.py` |
| 组装 | 各模式 `context/data.py` | engine 构建 RuntimeContext | pipeline 更新 RuntimeStatus |

## 用户策略 import（公开面）

策略作者与 extensions **只**从以下路径 import，勿使用 `core.engines.*` 内部路径：

```python
from core.modules.strategy.contracts import (
    CalendarAsOfResult,
    DataContext,
    Opportunity,
    StrategyHooks,
)
```

`CalendarAsOfContext` 等同理；`Strategy` facade 亦可在包根 import：

```python
from core.modules.strategy import DataContext, Opportunity, Strategy, StrategyHooks
```

`core.hooks.*` 为模块内部路径，用户策略勿直接 import。

## settings.data 声明

见各模式 README；字段 **`data_key`** + **`base` / `required`**（breaking，无旧字段）。

---

**Requires**: core>=0.5.0
