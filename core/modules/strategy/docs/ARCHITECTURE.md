# Strategy — 架构

**模块：** `modules.strategy` · **版本：** `0.7.0`

---

## 定位

策略执行 Facade：scan / enumerate / price_factor / portfolio / simulate。引擎通过 BacktestEngine `RunCallbacks` 挂进回测器；可变状态挂在 `JobContext.init`。

---

## 分层

```text
Strategy (Facade)
├── core/services/     discovery, entity_loader, simulation_cache, package, progress
├── core/engines/
│   ├── scanner/
│   ├── enumerator/    entity_based / slice_based
│   ├── price_factor/
│   └── portfolio/     不走 BE
└── core/hooks/        StrategyHooks / StrategyContext
```

---

## 与 BacktestEngine

| 组件 | 职责 |
|------|------|
| BE | jobs 调度、Timeline、`JobContext` |
| Strategy 引擎 | JobBuilder + JobExecutor + Pipeline |

portfolio 不用 BE；price_factor 业务在 after_task 事件回放。

---

## 相关文档

- [API.md](../API.md)
- [DESIGN.md](./DESIGN.md)
