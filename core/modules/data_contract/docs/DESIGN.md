# Data Contract 设计说明

**版本：** `0.2.0`

本文档描述 **`DataSpec` 字段**、**core 默认路由表摘要**、**缓存策略**、**userspace 合并**及 **Tag 专用 `DataKey.TAG`**。实现以 `mapping.py`、`data_contract_manager.py`、`cache/policy.py`、`discovery.py` 为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## `DataSpec`（`TypedDict`，字段均可选）

| 字段 | 含义 |
| --- | --- |
| `scope` | `ContractScope.GLOBAL` 或 `PER_ENTITY`。 |
| `type` | `ContractType.TIME_SERIES` 或 `NON_TIME_SERIES`。 |
| `unique_keys` | `validate_raw` 时要求行记录上存在的列（轻量校验）。 |
| `time_axis_field` / `time_axis_format` | 时序模板使用（如 `date` + `YYYYMMDD`，或 `quarter` + `YYYYQ`）。 |
| `loader` | `BaseLoader` 子类（非实例）。 |
| `entity_list_data_id` | 部分 per-entity loader 依赖的全局列表类 `DataKey`（如股票池）。 |
| `display_name` | 展示用名称。 |
| `defaults` | 与 `issue(..., **override_params)` 合并为 `loader_params`，后者覆盖前者。 |

---

## Core `default_map` 摘要

| `DataKey` | scope | type | 说明（loader） |
| --- | --- | --- | --- |
| `STOCK_LIST` | GLOBAL | 非时序 | 股票列表 |
| `STOCK_KLINE` | PER_ENTITY | 时序 | 股票 K 线（`adjust`/`term` 等由 params） |
| `TAG` | PER_ENTITY | 时序 | 标签值（scenario 等由 params / loader） |
| `STOCK_CORPORATE_FINANCE` | PER_ENTITY | 时序 | 财报季频 |
| `STOCK_ADJ_FACTOR_EVENTS` | PER_ENTITY | 时序 | 复权事件 |
| `INDEX_LIST` | GLOBAL | 非时序 | 指数列表 |
| `INDEX_KLINE_DAILY` | PER_ENTITY | 时序 | 指数日线 |
| `INDEX_WEIGHT_DAILY` | PER_ENTITY | 时序 | 指数权重 |
| `MACRO_*` | GLOBAL | 时序 | 宏观序列（GDP/LPR/CPI/PPI/PMI） |

完整默认值与字段以 `mapping.py` 为准。

---

## `issue` 与时间窗

- **非时序**：`start`/`end` 不参与业务语义；DCM 内部用占位窗口参与 cache key（见 `DataContractManager._effective_load_window`）。
- **时序**：须 **同时提供** `start` 与 `end`，或 **同时省略**（省略表示 **全量语义**，内部用 `__full__` 标记参与缓存键）。只传其一 → **`ValueError`**。
- **PER_ENTITY**：`entity_id` 必须非空字符串；GLOBAL 映射下误传的 `entity_id` 在 DCM 内会被忽略以免污染缓存键。

---

## 缓存范围（`resolve_cache_scope`）

| mapping 条件 | `ContractCacheScope` |
| --- | --- |
| GLOBAL + 非时序 | `GLOBAL`（进程级共享 store） |
| GLOBAL + 时序 | `PER_STRATEGY`（单次策略 run 内共享，随 `enter/exit_strategy_run` 清理） |
| 其他（含全部 PER_ENTITY） | `NONE`（不写缓存；`issue` 仅装配句柄，数据依赖 `load`） |

`DataContractManager.issue`：若 scope 为 NONE，直接 **`issuer.issue`**；若为 GLOBAL/PER_STRATEGY，则按 sha256 键尝试 **get → 命中则克隆 data 到 contract**；未命中则 **`contract.load(start=eff_start, end=eff_end)`** 后 **put** 再返回。

---

## Userspace 合并

- 文件：`userspace/data_contract/mapping.py`（路径由 `PathManager.data_contract_mapping()` 解析）。
- 导出变量名（优先级）：`custom_map` → `default_map` → `DATA_CONTRACT_MAP`。
- 键：**`DataKey` 实例或与已有枚举值相同的 `str`**（通过 `DataKey(key)` 构造）；须与 **core 已定义的 `DataKey` 成员**一致，**不得与 core 已有键重复**（重复 → `ValueError`）。
- 新增「全新」业务 id 需要先在 **`contract_const.DataKey`** 中增加枚举成员（core 变更），再在 userspace 提供对应 `DataSpec`。

---

## `DataKey.TAG`（标签）

映射为 **PER_ENTITY + TIME_SERIES**，时间轴字段 **`as_of_date`**；具体场景（scenario）由 **`TagLoader`** 与 `loader_params`（如 `tag_scenario` / `scenario_id`）解析，与标签元数据一致。

---

## 相关文档

- [API.md](API.md)
- [DECISIONS.md](DECISIONS.md)
