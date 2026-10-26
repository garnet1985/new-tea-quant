# Data Contract — 决定

**版本：** `0.4.3`

本文列出声明式取数模块的关键选型回顾。  
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

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
- [设计思路](./DESIGN.md)
- [概念](./CONCEPTS.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
