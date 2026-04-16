# Data Contract 模块 API 文档

本文档采用统一 API 条目格式：函数名、状态、描述、诞生版本、参数（三列表格）、返回值。

包级常用导出见 `core.modules.data_contract` 的 `__all__`；下文含内部协作类型（如 `ContractIssuer`）仅作索引时可略。

---

## DataContractManager

### 函数名
`__init__(self, *, contract_cache: ContractCacheManager) -> None`

- 状态：`stable`
- 描述：构造管理器：合并 `default_map` 与 userspace 映射、创建 **`ContractIssuer`**、持有 **`ContractCacheManager`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `contract_cache` | `ContractCacheManager` | 进程内缓存实例 |

- 返回值：`None`

---

### 函数名
`issue(self, data_id: DataKey, *, entity_id: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, **override_params: Any) -> DataContract`

- 状态：`stable`
- 描述：签发 **`DataContract`**。对 **`ContractCacheScope` 非 `NONE`** 的规格：尝试读缓存；未命中则 **`load`** 后写入缓存并把 **`data`** 拷回句柄。对 **`NONE`**：仅 **`issuer.issue`**，**`data` 一般为空**，需调用方再 **`load`**。参数与缓存语义见 [`DECISIONS.md`](DECISIONS.md)。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `data_id` | `DataKey` | 必选；须在合并后的 `map` 中存在 |
| `entity_id` (可选) | `Optional[str]` | `PER_ENTITY` 时必填非空 |
| `start` (可选) | `Optional[str]` | 时序：与 `end` 同传或同省略 |
| `end` (可选) | `Optional[str]` | 时序：与 `start` 同传或同省略 |
| `**override_params` | `Any` | 覆盖 mapping 中 `defaults` 的 loader 参数 |

- 返回值：`DataContract`

---

## ContractCacheManager

### 函数名
`__init__(self) -> None`

- 状态：`stable`
- 描述：创建 **global** 与 **per-strategy** 两个 store。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`enter_strategy_run(self) -> None`

- 状态：`stable`
- 描述：单次策略 run 开始：清空 **per-strategy** 层（可与 `exit_strategy_run` 对称使用）。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`exit_strategy_run(self) -> None`

- 状态：`stable`
- 描述：单次策略 run 结束：清空 **per-strategy** 层。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`clear_global(self) -> None`

- 状态：`stable`
- 描述：清空 **global** 层缓存。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`clear_all(self) -> None`

- 状态：`stable`
- 描述：清空 global 与 per-strategy 两层。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`get(self, cache_scope: ContractCacheScope, key: str) -> Optional[ContractCacheEntry]`

- 状态：`stable`
- 描述：按层读取缓存条目（通常由 **`DataContractManager`** 内部使用）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `cache_scope` | `ContractCacheScope` | `GLOBAL` / `PER_STRATEGY` 等 |
| `key` | `str` | 缓存键 |

- 返回值：`ContractCacheEntry` 或 `None`

---

### 函数名
`put_for_scope(self, cache_scope: ContractCacheScope, key: str, *, meta: Optional[Dict[str, Any]] = None, data: Any = None) -> None`

- 状态：`stable`
- 描述：写入缓存；`cache_scope == NONE` 时不写。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `cache_scope` | `ContractCacheScope` | 目标层 |
| `key` | `str` | 缓存键 |
| `meta` (可选) | `Optional[Dict[str, Any]]` | 元数据 |
| `data` (可选) | `Any` | 载荷 |

- 返回值：`None`

---

### 函数名
`put_entry(self, cache_scope: ContractCacheScope, key: str, entry: ContractCacheEntry) -> None`

- 状态：`stable`
- 描述：以完整 **`ContractCacheEntry`** 写入；`NONE` 时不写。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `cache_scope` | `ContractCacheScope` | 目标层 |
| `key` | `str` | 缓存键 |
| `entry` | `ContractCacheEntry` | 条目 |

- 返回值：`None`

---

## resolve_cache_scope

### 函数名
`resolve_cache_scope(spec: DataSpec) -> ContractCacheScope`

- 状态：`stable`
- 描述：根据 **`DataSpec`** 的 `scope` 与 `type` 决定缓存层；见 [`DESIGN.md`](DESIGN.md)。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `spec` | `DataSpec` | 单条映射 |

- 返回值：`ContractCacheScope`

---

### 函数名
`resolve_cache_scope_for_data_key(dcm_map: DataSpecMap, data_id: DataKey) -> ContractCacheScope`

- 状态：`stable`
- 描述：对 **`dcm_map`** 查 `data_id` 后调用 **`resolve_cache_scope`**；不存在时返回 **`NONE`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `dcm_map` | `DataSpecMap` | 合并后的映射 |
| `data_id` | `DataKey` | 键 |

- 返回值：`ContractCacheScope`

---

## discover_userspace_map

### 函数名
`discover_userspace_map() -> DataSpecMap`

- 状态：`stable`
- 描述：若存在 **`userspace.data_contract.mapping`** 且导出映射变量，则解析为 **`DataSpecMap`**；否则返回空字典。键经 **`DataKey`** 规范化。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`DataSpecMap`

---

## DataContract

### 函数名
`needs_load(self) -> bool`

- 状态：`stable`
- 描述：属性语义：`True` 表示 **`data is None`**，仍需 **`load`**。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`bool`

---

### 函数名
`get_meta(self) -> ContractMeta`

- 状态：`stable`
- 描述：返回 **`ContractMeta`**。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`ContractMeta`

---

### 函数名
`load(self, **override_params: Any) -> Any`

- 状态：`stable`
- 描述：合并 **`loader_params`** 与 `override_params` 后调用 **`loader.load(params, context)`**，结果写入 **`self.data`** 并返回。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `**override_params` | `Any` | 覆盖本次 load 的参数 |

- 返回值：loader 返回的任意类型（通常为行列表）

---

### 函数名
`validate_raw(self, raw: Any) -> Any`

- 状态：`beta`（基类透传；子类加强校验）
- 描述：对 **raw** 做校验/规范化；**`DataContract`** 基类默认透传 **`raw`**；**`TimeSeriesContract` / `NonTimeSeriesContract`** 实现轻量校验。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `raw` | `Any` | 裸数据 |

- 返回值：通过校验后的数据（当前多为原样或同结构）

---

### 函数名
`clear(self) -> None`

- 状态：`stable`
- 描述：将 **`data`** 置为 **`None`**。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

## DataKey（枚举）

字符串枚举，成员包括（值为其字符串）：`STOCK_LIST`、`STOCK_KLINE`、`TAG`、`STOCK_ADJ_FACTOR_EVENTS`、`STOCK_CORPORATE_FINANCE`、`INDEX_LIST`、`INDEX_KLINE_DAILY`、`INDEX_WEIGHT_DAILY`、`MACRO_GDP`、`MACRO_LPR`、`MACRO_CPI`、`MACRO_PPI`、`MACRO_PMI`。完整定义见 `contract_const.py`。

---

## 示例

```python
from core.modules.data_contract import (
    ContractCacheManager,
    DataContractManager,
    DataKey,
)

cache = ContractCacheManager()
dcm = DataContractManager(contract_cache=cache)

c = dcm.issue(DataKey.STOCK_LIST)
assert c.data is not None or c.needs_load
```

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
