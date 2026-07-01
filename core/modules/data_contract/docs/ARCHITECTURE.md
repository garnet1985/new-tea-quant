# Data Contract 架构文档

**版本：** `0.5.0`（Facade **`DataContracts`**；GLOBAL 黑盒 cache；公开契约 **`api.yaml`**）

---

## 模块介绍

`modules.data_contract` 将「策略/标签声明的数据依赖」收敛为 **`DataKey` → `DataSpec`** 路由，经 **注册 → 签发 → 句柄 → 加载 → 缓存** 流水线交付。PIT 前缀裁剪由 Facade **`DataContracts.until`** 委托独立模块 **`modules.data_cursor`**。

---

## 分层结构

```text
modules.data_contract/
├── data_contract.py      # Facade: DataContracts
├── contracts.py          # 跨模块公开类型（仅类/枚举）
├── api.yaml / glossary.yaml / OVERVIEW.md
├── core/
│   ├── registry/         # L1 路由注册（含 kline_keys 等内部 helper）
│   ├── issue/            # L2 签发与 load
│   ├── contract/         # L3 句柄与信封
│   ├── load/             # L4 Loader
│   ├── cache/            # L5 进程内 GLOBAL / per-strategy store
│   └── launcher/         # BFF catalog
├── docs/
└── __test__/
```

| 层 | 包 | 核心类型 | 职责 |
| --- | --- | --- | --- |
| **Facade** | `data_contract.py` | `DataContracts` | `info` / `issue` / `load` / `until` / 时间 helper |
| **L1 registry** | `core/registry/` | `DataKey`, `DataSpecMap` | core + userspace 映射合并 |
| **L2 issue** | `core/issue/` | `DataContractManager`, `ContractIssuer` | 参数校验、load、GLOBAL cache |
| **L3 contract** | `core/contract/` | `DataContract`, `IssueResult` | 句柄与返回信封 |
| **L4 load** | `core/load/` | `BaseLoader`, … | 取数 IO；`load_batch` |
| **L5 cache** | `core/cache/` | `ContractCacheManager` | 进程内 store（Facade 黑盒持有） |

**与 data_cursor 的关系：** `modules.data_cursor` 仍为独立模块。跨模块 import：句柄类型用 **`contracts.py`**；cursor 用 **`core.modules.data_cursor`**。

---

## 架构 / 流程图

```mermaid
flowchart TB
  subgraph L1 [L1 registry]
    M[default_map]
    U[userspace mapping]
  end
  subgraph Facade [DataContracts]
    F[issue / load / until]
  end
  subgraph L3 [L3 contract]
    DC[DataContract]
  end
  subgraph L4 [L4 load]
    L[BaseLoader]
  end
  subgraph L5 [L5 cache GLOBAL only]
    C[shared_contract_cache]
  end
  subgraph DCUR [modules.data_cursor]
    CUR[DataCursor.until]
  end
  M --> F
  U --> F
  F --> L
  F --> C
  F --> DC
  DC -->|until as_of| CUR
```

---

## 模块职责与边界

**职责（In scope）**

- 维护映射、签发句柄、协调 **GLOBAL** cache 与 load。
- Facade 暴露 **`until(as_of)`** 与时间窗 helper。

**边界（Out of scope）**

- cursor 状态机（**`modules.data_cursor`**）。
- DB schema / SQL（**`modules.data_manager`**）。
- PER_ENTITY Parquet 磁盘缓存（**未来**，见 [`ROADMAP.md`](ROADMAP.md) 阶段 6）。

---

## 相关文档

- [OVERVIEW.md](../OVERVIEW.md)
- [api.yaml](../api.yaml)
- [modules.data_cursor](../../data_cursor/README.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
- [ROADMAP.md](ROADMAP.md)
