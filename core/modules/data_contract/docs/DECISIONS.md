# Data Contract — 设计与决策

**版本：** `0.4.3`

本文记录声明式取数模块的设计目标、方案思路与拍板决策。API 以根目录 [API.md](../API.md) 为准，名词见 [CONCEPTS.md](./CONCEPTS.md) / [glossary.yaml](../glossary.yaml)。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

提供一套可扩展的数据声明到数据加载的契约，实现回测过程中的声明式数据注入：上层只声明需要什么数据，由模块把声明翻译成实际加载。声明式数据保证可追踪、可缓存、可校验；用户可扩展数据源而不改 core。

## 方案与思路

- **单一门面**：包根仅导出 `ContractIssuer`；推荐静态入口 `ContractIssuer.issue(key, entity_ids=…, runtime=…, fill_in_data=…)`；首次 `issue` / 类方法会自动 discovery，实例路径可显式 `discover()`（见 DEC-01）。
- **契约三层**：声明分 meta（声明期 key、type、scope、loader、`list_data_key` 等）、runtime（签发后 entity_ids、时间窗等参数）、specific（契约特有扩展字段）三层；时序句柄为 `BaseTimeSeriesContract`，`until(as_of)` 推进内置 `CursorState`（见 DEC-02）。
- **Scope 二分**：GLOBAL 共享一份数据（`fill_in_data` → `loader.load`）；PER_ENTITY 须 `entity_ids`，单实体 `load`、多实体优先 `load_batch`；`meta.list_data_key` 指向 PER_ENTITY 所属宇宙的 GLOBAL list（如 `stock.kline.daily` → `stock.list`）（见 DEC-03）。
- **系统 key 与 userspace 扩展并存**：系统 key 在 `core/data_contracts/data_keys.py` 的 `SYS_DATA_KEY`，经 `contracts.DATA_KEY` 暴露；用户扩展经 userspace `data_keys`（`USER_DATA_KEY`）+ `data_contracts/<key>/`，discovery 合并进可用 key 集（见 DEC-04）。
- **应用层边界**：settings 声明的 `required_data` / extras 走 contract；编排用股票池 / 日历等（未声明）可由应用直调其它服务，一旦写入 extras 则走 contract（见 DEC-05）。

---

## DEC-01：包根仅导出 ContractIssuer

**是什么：** 模块唯一公开入口是 `ContractIssuer`，内部 loader / contract 子类不导出。

**为什么选它：**

- 单一门面收敛调用面
- 内部实现可自由演进，不破坏外部调用

**放弃了什么：**

- **导出 BaseDataContractLoader 等基类：** 供用户扩展 — 基类属于契约包内部，用户扩展通过 userspace 契约目录而非 import 基类

---

## DEC-02：契约三层：meta / runtime / specific

**是什么：** 契约声明分三层——meta（声明期 key/type/scope/loader）、runtime（签发后 entity_ids/时间窗）、specific（契约特有扩展字段）。

**为什么选它：**

- 声明与运行时参数分离，meta 可静态校验
- specific 允许个别契约扩展字段而不污染通用结构

**放弃了什么：**

- **扁平单层：** 所有字段平铺 — 声明与运行时混杂，校验困难

---

## DEC-03：Scope 二分：GLOBAL vs PER_ENTITY

**是什么：** 契约 scope 只有两种——GLOBAL（共享一份）与 PER_ENTITY（按实体各一份）。

**为什么选它：**

- 覆盖当前所有数据访问场景：宏观 / 日历是 GLOBAL，K 线 / 财报是 PER_ENTITY
- 二分简单明确，新增 scope 需强理由

**放弃了什么：**

- **支持自定义 scope：** 如 PER_INDUSTRY / PER_DATE — 当前无需求，过度设计

---

## DEC-04：系统 key 与 userspace 扩展并存

**是什么：** 系统契约在 `core/data_contracts/<key>/`，用户扩展在 `userspace/data_contracts/<key>/`；discovery 合并进可用 key 集。

**为什么选它：**

- 用户可扩展数据源而不改 core
- 系统契约作为内置默认，开箱即用

**放弃了什么：**

- **仅系统契约：** 用户无法扩展 — 数据源接入必须改 core，违背插件化原则

---

## DEC-05：应用层边界：settings 声明走 contract，未声明直调

**是什么：** settings 里 `required_data` / extras 声明的数据走 contract；编排用股票池 / 日历等未声明的可由应用直调其它服务。

**为什么选它：**

- 声明式数据保证可追踪、可缓存、可校验
- 编排逻辑（如枚举器自己需要股票列表）不属于策略数据，不应强制走 contract

**放弃了什么：**

- **一切数据访问走 contract：** 统一但僵化 — 编排内部数据访问也走 contract 会引入不必要的抽象层

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
