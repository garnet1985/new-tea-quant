# Data Contract 术语与概念

**版本：** `0.3.3`（`IssueResult` / `load_batch`：**已实现**）

本文档固定 **名词含义**，避免与历史草稿或外部文章混读。实现位置以仓库内代码为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## 1. 核心名词

| 术语 | 含义 |
| --- | --- |
| **DataKey** | 数据依赖的稳定标识（`contract_const.DataKey` 枚举）；Strategy/Tag 在 settings 中声明「要什么」。 |
| **DataSpec / DataSpecMap** | 单个 key 的路由说明 / 全表映射（`mapping.py`）。 |
| **DataContract** | 句柄：`meta`、`loader`、`loader_params`、`context`、可选 **`data`**（`contracts/base.py`）。**每个句柄对应一个 entity 的 payload**（PER_ENTITY）或全局 payload（GLOBAL）。 |
| **IssueResult** | **`issue`** 的返回信封（0.3.0）：GLOBAL → **`contract`**；PER_ENTITY → **`by_entity: Mapping[str, DataContract]`**。 |
| **issue** | **`DataContractManager.issue`**：解析映射、校验参数、经 loader 物化数据；PER_ENTITY 走 **`load_batch` 优先** 路径。 |
| **load** | **`DataContract.load`** 或 loader **`load`**：单 entity 取数。 |
| **load_batch** | **`BaseLoader.load_batch`**（0.3.0）：多 entity 取数，返回 **`Mapping[entity_id, raw]`**；默认实现为循环 **`load`**。 |
| **validate_raw** | **`DataContract` / 子类**：对已取得的 **raw** 做轻量字段校验（`TimeSeriesContract` / `NonTimeSeriesContract`）；主线可在取数后显式调用，不阻塞 issue/load 默认路径。 |

---

## 2. Scope 与类型

| 术语 | 含义 |
| --- | --- |
| **ContractScope** | `GLOBAL`：不按单票分片，**`issue` → `IssueResult.contract`**；`PER_ENTITY`：绑定 **一个或多个 `entity_id`**，**`issue` → `IssueResult.by_entity`**（map）。 |
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
3. **`BaseLoader` 实现**：在 `loaders/` 中实现 **`load(params, context)`**；可选 override **`load_batch(entity_ids, params, context)`** 以启用 bulk IO（见 [`DECISIONS.md`](DECISIONS.md) 决策 10）。

仅写 mapping 未提供可实例化 loader → **`issue` 在签发阶段失败**。

Strategy / Tag **不应**对 **settings 已声明** 的 `DataKey` 再直调 `DataManager`（决策 11）；扩展取数能力应 **只改 loader**。

---

## 5. 应用层边界（Strategy / Tag）

Contract 只覆盖 **用户声明的数据依赖**；回测编排不在默认范围内。

| 类别 | 走 contract？ | 示例 |
| --- | --- | --- |
| `data.base_required_data` | ✅ 必须 | 有且仅一条 `stock.kline.{daily\|weekly\|monthly}`，运行时主 slot 为 `klines` |
| `data.extra_required_data_sources` | ✅ 必须 | 用户声明的 macro、tag、其他周期 K 线等；**同一 `data_id` 不可重复** |
| 回测 **股票池 / universe** | ❌ 默认否 | `resolve_backtest_universe` → `stock.list.load` |
| 单票 **元数据** | ❌ 默认否 | `load_meta` / `load_single` |
| **交易日历**、最新交易日 | ❌ 否 | `CalendarService`、date resolve |
| 用户 **把 `stock.list` 写进 extras** | ✅ 是 | 声明即纳入 contract，不得旁路 |

注入入口：`StrategyDataInjectionService.required_data_sources`（= base + extras）；job 级批量见 `StrategyJobContractBatch`。
