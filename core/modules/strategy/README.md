# Strategy 模块（`modules.strategy`）

**`StrategyManager`** 在 **`userspace/strategies/`** 下发现策略（**`settings.py`** + **`strategy_worker.py`**），提供 **`scan`**（最新日扫描）与 **`simulate`**（逐日主线回测）。**`OpportunityEnumerator`** 产出 **CSV 枚举事实表**，**`PriceFactorSimulator`** / **`CapitalAllocationSimulator`** 在其上叠加价格层与资金层模拟。

深入教程见 **[策略开发](../../../userspace/strategies/USER_GUIDE.md)**。子目录职责见 **[docs/components/](docs/components/README.md)**。

## 适用场景

- 配置驱动自定义因子/形态，需 **扫描 → 验证 → 组合回测** 分层迭代。
- 需要 **一次枚举、多次复用** 的 CSV 缓存，供双模拟器与分析共用。

## 快速开始

```python
from core.modules.strategy import StrategyManager

mgr = StrategyManager()
mgr.scan() # 所有启用策略，默认今日
# mgr.scan("my_strategy", date="20260101")
# mgr.simulate("my_strategy")
```

枚举与模拟器：

```python
from core.modules.strategy.components import OpportunityEnumerator, PriceFactorSimulator
from core.modules.strategy.components.simulator.capital_allocation import CapitalAllocationSimulator

# OpportunityEnumerator.enumerate("my_strategy", "20200101", "20251231", stock_list, max_workers="auto")
# PriceFactorSimulator().run("my_strategy")
# CapitalAllocationSimulator().run("my_strategy")
```

## 目录结构（节选）

```text
core/modules/strategy/
├── module_info.yaml
├── README.md
├── strategy_manager.py
├── base_strategy_worker.py
├── components/          # 见 docs/components/
├── helpers/
├── managers/
├── models/
├── data_classes/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    ├── DECISIONS.md
    └── components/
```

## 模块依赖（`module_info.yaml`）

含 **`modules.data_manager`**、**`modules.data_contract`**、**`modules.data_cursor`**、**`modules.indicator`**、**`modules.adapter`**、**`infra.project_context`**、**`infra.worker`**。

## 相关文档

- [架构与边界](docs/ARCHITECTURE.md)
- [四层与设计要点](docs/DESIGN.md)
- [公开 API](docs/API.md)
- [设计决策](docs/DECISIONS.md)
- [组件细分](docs/components/README.md)
