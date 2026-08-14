# Data Contract 设计说明

**模块：** `modules.data_contract` · **版本：** `0.4.0`

API 以根目录 [API.md](../API.md) 为准。名词见 [CONCEPTS.md](./CONCEPTS.md) / [glossary.yaml](../glossary.yaml)。

---

## 1. Facade：`ContractIssuer`

- 包根仅导出 `ContractIssuer`
- 推荐静态入口：`ContractIssuer.issue(key, entity_ids=…, runtime=…, fill_in_data=…)`
- 首次 `issue` / 类方法会自动 discovery；实例路径可显式 `discover()`

---

## 2. 契约三层：meta / runtime / specific

| 层 | 含义 |
| --- | --- |
| **meta** | 声明期：key、type、scope、loader、`list_data_key`（PER_ENTITY）等 |
| **runtime** | 签发后：entity_ids、时间窗、adjust 等参数 |
| **specific** | 契约特有扩展字段 |

时序句柄为 `BaseTimeSeriesContract`：`until(as_of)` 推进内置 `CursorState`（无独立 data_cursor 包）。

---

## 3. Scope 与取数

| Scope | 行为 |
| --- | --- |
| **GLOBAL** | 共享一份数据；`fill_in_data` → `loader.load` |
| **PER_ENTITY** | 须 `entity_ids`；单实体 `load`，多实体优先 `load_batch` |

`meta.list_data_key`：PER_ENTITY 所属宇宙的 GLOBAL list（如 `stock.kline.daily` → `stock.list`）。

---

## 4. 系统 key 与 userspace 扩展

系统 key：`core/data_contracts/data_keys.py` → `SYS_DATA_KEY`，经 `contracts.DATA_KEY` 暴露。

每个 key 包布局：

| 文件 | 要求 | 说明 |
| --- | --- | --- |
| `declaration.py` | 必需 | meta（type/scope/loader；PER_ENTITY 含 `list_data_key`） |
| `loader.py` | 通常必需 | `BaseDataContractLoader`；若 `contract_class` 自管取数可省略职责外移 |
| `contract.py` | 可选 | 自定义子类，经 `meta.contract_class` 挂载（如 ST 状态查询、Tag） |

新增系统契约：

1. 按上表建立 `core/data_contracts/<key>/`
2. 在 `SYS_DATA_KEY` 增加常量；declaration 的 `meta.key` 使用该常量
3. 若专用子类需跨模块类型提示，在 `contracts.py` 再导出（如 `StockStPeriodsContract`）

用户扩展：userspace `data_keys`（`USER_DATA_KEY`）+ `data_contracts/<key>/`；discovery 合并进可用 key 集。

---

## 5. 与应用层边界

| 类别 | 走 contract？ |
| --- | --- |
| settings 声明的 `required_data` / extras | ✅ |
| 编排用股票池 / 日历等（未声明） | ❌ 可由应用直调其它服务；一旦写入 extras 则走 contract |

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [CONCEPTS.md](./CONCEPTS.md)
