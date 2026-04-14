# Data Contract 术语与概念

**版本：** `0.2.0`

本文档固定 **名词含义**，避免与历史草稿或外部文章混读。实现位置以仓库内代码为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## 1. 核心名词

| 术语 | 含义 |
| --- | --- |
| **DataKey** | 数据依赖的稳定标识（`contract_const.DataKey` 枚举）；Strategy/Tag 在 settings 中声明「要什么」。 |
| **DataSpec / DataSpecMap** | 单个 key 的路由说明 / 全表映射（`mapping.py`）。 |
| **DataContract** | 句柄：`meta`、`loader`、`loader_params`、`context`、可选 **`data`**（`contracts/base.py`）。 |
| **issue** | **`DataContractManager.issue`**：解析映射、校验参数、可能经缓存 **物化 `data`**。 |
| **load** | **`DataContract.load`**：调用已绑定 **`BaseLoader.load`**，写入 **`data`**。 |
| **validate_raw** | **`DataContract` / 子类**：对已取得的 **raw** 做轻量字段校验（`TimeSeriesContract` / `NonTimeSeriesContract`）；主线可在取数后显式调用，不阻塞 issue/load 默认路径。 |

---

## 2. Scope 与类型

| 术语 | 含义 |
| --- | --- |
| **ContractScope** | `GLOBAL`：不按单票分片；`PER_ENTITY`：绑定单一 `entity_id`（如股票、指数）。 |
| **ContractType** | `TIME_SERIES`：时间轴维度存在；`NON_TIME_SERIES`：无统一时间轴字段的清单/映射类。 |

是否「时序」以 **mapping 中 `type`** 与存储字段约定为准，而不是仅看查询方式。

---

## 3. 代码入口（当前仓库）

| 内容 | 位置 |
| --- | --- |
| `DataKey` / `ContractScope` / `ContractType` | `contract_const.py` |
| core 路由表 | `mapping.py` → `default_map` |
| userspace 合并 | `discovery.py` → `discover_userspace_map` |
| 签发句柄 | `contract_issuer.py` |
| 对外 `issue` + 缓存 | `data_contract_manager.py` |
| 缓存策略 | `cache/policy.py` → `resolve_cache_scope` |
| Loader 基类 | `loaders/base.py` |

---

## 4. Userspace 扩展（三要素）

新增一种可被声明的数据依赖时，需要 **一致** 的：

1. **`DataKey`**：在 **`contract_const.py`** 增加枚举成员（core 白名单）。  
2. **`DataSpec`**：在 **`default_map`**（或仅 userspace 映射，若 key 已存在 core 枚举）中填写 scope、type、loader、键字段等。  
3. **`BaseLoader` 实现**：在 `loaders/`（或 userspace loaders 目录，由 mapping 引用）中实现 `load(params, context)`。

仅写 mapping 未提供可实例化 loader → **`issue` 在签发阶段失败**。
