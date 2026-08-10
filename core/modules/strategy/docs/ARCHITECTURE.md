# Strategy — 架构

**版本：** `0.6.0`

`modules.strategy` 对外仅暴露 **`Strategy`**：机会扫描、模拟三步（enumerate / price_factor / portfolio）、结果摘要与策略发现。引擎经 BacktestEngine `RunCallbacks` 挂入回测；可变业务状态挂在 `JobContext.init`。

---

## 职责与边界（结论）

**负责**

- 策略包发现与 Facade 编排（指纹 → 缓存 → Pipeline）
- Scanner / Enumerator / PriceFactor / Portfolio 引擎与报告
- userspace hooks 契约（`StrategyHooks` / `StrategyContext`）
- 模拟产物路径与工作台缓存槽

**不负责**

- 不另起平行于 BacktestEngine 的调度 / Timeline / JobSession
- 不 deep-export 引擎实现（跨模块优先 `Strategy` + `contracts`）

硬约束细节见 [DESIGN.md](./DESIGN.md) 与 [notes/BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)。

---

## 模块结构图

```text
strategy/
├── __init__.py              # 导出 Strategy
├── contracts.py             # hooks / 枚举 / 共享数据类
├── API.md / glossary.yaml
├── __test__/test_api.py     # 公开契约
└── core/
    ├── strategy.py          # Facade 实现
    ├── enums.py
    ├── hooks/
    ├── helpers/
    ├── services/            # discovery, entity_loader, simulation_cache, package, progress
    └── engines/
        ├── scanner/
        ├── enumerator/      # entity_based / slice_based
        ├── price_factor/
        ├── portfolio/       # 不走 BE
        └── shared/
```

---

## 架构图

```mermaid
flowchart TB
  Caller --> Facade[Strategy]
  Facade --> Scan[ScannerPipeline]
  Facade --> Sim[simulate 指纹/缓存]
  Sim --> Enum[EnumeratorPipeline]
  Sim --> Price[PriceFactorPipeline]
  Sim --> Port[PortfolioPipeline]
  Enum --> BE[BacktestEngine]
  Price --> BE
  Facade --> Disc[DiscoveryService]
```

---

## 与 BacktestEngine

| 组件 | 职责 |
|------|------|
| BE | jobs 调度、Timeline、`JobContext`、slice 装载 |
| Strategy 引擎 | JobBuilder + JobExecutor + Pipeline |

portfolio 不用 BE；price_factor 业务在 after_task 事件回放。

---

## 相关文档

- [API.md](../API.md)
- [glossary.yaml](../glossary.yaml)
- [DESIGN.md](./DESIGN.md)
- [BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)
