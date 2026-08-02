# Strategy API 文档

**版本：** `0.7.0`  
**最低支持核心版本：** `>=0.4.4`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。

**公开约定：** 包根仅导出 `Strategy`；hooks 与枚举从 [`contracts.py`](./contracts.py) 导入。

---

## Strategy

**描述：** 策略 Facade — scan / enumerate / analyze / discovery / simulate

### scan

`Strategy.scan(key_or_id=None, *, demo=False) -> Dict[str, Any]`

- **状态：** `beta`

### enumerate

`Strategy.enumerate(strategy_name, *, userspace_root=None, strategies_root=None) -> Dict[str, Any]`

- **状态：** `beta`

### analyze / list_strategies / get_strategy_info

- **状态：** `stable` / `beta`（见源码 docstring）

**举例：**

```python
from core.modules.strategy import Strategy

result = Strategy.enumerate("demo/random/random_v1_null_baseline")
Strategy.scan("demo_strategy")
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `StrategyHooks` / `StrategyContext` / `StrategyData` / `StrategyInfo` | userspace hook 契约 |
| `Opportunity` / `Investment` / `CalendarAsOfResult` | 引擎共享数据类 |
| `ExecutionMode` / `SellReason` / `SimulateKind` / `WorkbenchStep` | 公开枚举 |
