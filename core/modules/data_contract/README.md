# Data Contract 模块（`modules.data_contract`）

用 **`DataKey`** 声明「要哪类数据」，由 **`DataSpecMap`**（core `default_map` + userspace 合并）描述 **scope、时序/非时序、loader、唯一键、时间轴字段** 等；**`DataContractManager.issue`** 统一签发 **`DataContract`** 句柄，并在 **可缓存的 GLOBAL** 场景下按需 **物化 `data`**；**`PER_ENTITY`** 等则句柄上 **`data` 为空**，需再 **`load(start=..., end=...)`**。Strategy / Tag 等通过 **`ContractCacheManager`** 在 run 边界清理缓存。

## 适用场景

- 策略或标签侧按 **`DataKey`** 取数，避免散落字符串绑表。
- 需要 **GLOBAL 清单类数据** 在进程内复用（如股票列表）或 **GLOBAL 时序宏观数据** 按策略 run 缓存。
- 在 **`userspace/data_contract/mapping.py`** 中 **追加** 与 core **不重复** 的 `DataKey` 映射（键须为已定义的 `DataKey` 枚举成员）。

## 快速开始

```python
from core.modules.data_contract import (
    ContractCacheManager,
    DataContractManager,
    DataKey,
)

cache = ContractCacheManager()
cache.enter_strategy_run()
dcm = DataContractManager(contract_cache=cache)

# GLOBAL 非时序：issue 时可能已物化 data（视缓存命中）
c = dcm.issue(DataKey.STOCK_LIST)
rows = c.data if c.data is not None else c.load()

# PER_ENTITY 时序：须 entity_id；数据通常需再 load
k = dcm.issue(
    DataKey.STOCK_KLINE,
    entity_id="000001.SZ",
    start="20240101",
    end="20241231",
    adjust="qfq",
    term="D",
)
data = k.load()
cache.exit_strategy_run()
```

更多参数与缓存语义见 [`docs/DECISIONS.md`](docs/DECISIONS.md) 与 [`docs/DESIGN.md`](docs/DESIGN.md)。

## 目录结构（本模块）

```text
core/modules/data_contract/
├── module_info.yaml
├── README.md
├── data_contract_manager.py
├── contract_issuer.py
├── contract_const.py      # DataKey / ContractScope / ContractType
├── mapping.py               # default_map
├── discovery.py
├── contracts/
├── loaders/
├── cache/
├── data_class/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    ├── DECISIONS.md
    └── CONCEPTS.md
```

## 模块依赖（`module_info.yaml`）

- **`modules.data_manager`**：各 `BaseLoader` 实现通过 `DataManager` 等取数。
- **`infra.project_context`**：`discover_userspace_map` 使用路径管理器定位 `userspace/data_contract`。

## 测试

在仓库根目录：

```bash
python3 -m pytest core/modules/data_contract/__test__/ -q
```

## 相关文档

- [架构与边界](docs/ARCHITECTURE.md)
- [设计与映射](docs/DESIGN.md)
- [公开 API](docs/API.md)
- [设计决策（issue / 缓存）](docs/DECISIONS.md)
- [术语与概念](docs/CONCEPTS.md)
