# Data Contract 术语与概念

**版本：** `0.6.0`

与 [glossary.yaml](../glossary.yaml) 对齐；实现以仓库代码为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## 1. 核心名词

| 术语 | 含义 |
| --- | --- |
| **DATA_KEY** | 数据依赖的稳定标识（`contracts.DATA_KEY` / `SYS_DATA_KEY`） |
| **ContractIssuer** | 发现与签发 Facade；推荐 `issue(...)` |
| **BaseDataContract** | 句柄：meta / runtime / specific；可选已填充 `data` |
| **issue** | 按 key 签发实例；可选立即 `fill_in_data` |
| **fill_in_data** | 调 loader 物化数据（GLOBAL/`load`；PER_ENTITY 单/批） |
| **until** | 时序 PIT：把可见数据推进到 `as_of`（`CursorState`） |

---

## 2. Scope 与类型

| 术语 | 含义 |
| --- | --- |
| **ContractScope.GLOBAL** | 全实体共享一份 payload |
| **ContractScope.PER_ENTITY** | 按 `entity_ids` 分片；须 `list_data_key` |
| **ContractType.TIME_SERIES** | 有统一时间轴字段 |
| **ContractType.NON_TIME_SERIES** | 清单/映射类，无统一时间轴 |

---

## 3. 代码入口

| 内容 | 位置 |
| --- | --- |
| Facade | `from core.modules.data_contract import ContractIssuer` |
| 键与基类 | `from core.modules.data_contract.contracts import DATA_KEY, …` |
| 系统 key 表 | `core/data_contracts/data_keys.py` |
| 各契约实现 | `core/data_contracts/<key>/` |
| Issuer 实现 | `core/discovery/contract_issuer.py` |

---

## 4. Userspace 扩展

1. **key**：userspace `USER_DATA_KEY`
2. **declaration.py**：meta（含 type/scope/loader；PER_ENTITY 含 `list_data_key`）
3. **loader.py**：继承 `BaseDataContractLoader`，实现 `load`（可选 `load_batch`）
4. **contract.py**（可选）：自定义子类 + `meta.contract_class`

---

## 5. 应用层边界

Contract 覆盖 **用户声明的数据依赖**。未声明的编排数据（宇宙、日历等）默认不强制走本模块；写入 settings extras 后则应走 `ContractIssuer`。
