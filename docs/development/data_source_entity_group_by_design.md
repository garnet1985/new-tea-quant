# Data Source 实体分组（Entity / Group By）设计整理

## 一、目标

1. **禁止推断**：框架不做任何隐式猜测，所有行为由配置显式声明
2. **用户代码简单**：大部分 handler 使用默认实现，零或极少量覆盖
3. **语义清晰**：配置与行为一一对应，作者和用户都能快速理解

---

## 二、实体分组涉及的完整业务链路

```
[实体列表] → [last_update 查询] → [entity_date_ranges] → [build jobs] → [fetch] → [fetched_data 分组] → [normalize]
```

每一步都依赖「实体」的定义，必须统一且显式。

---

## 三、现有用例与差异

### 3.1 用例清单

| # | Handler | 实体维度 | 实体列表来源 | 实体 ID 格式 | API 参数名 | last_update 分组 | 特殊逻辑 |
|---|---------|----------|--------------|--------------|------------|------------------|----------|
| 1 | corporate_finance | 单字段：股票 | stock_list | id (ts_code) | ts_code | 按 id | 无 |
| 2 | stock_indicators | 单字段：股票 | stock_list | id (ts_code) | ts_code | 按 id | 无 |
| 3 | index_klines | 单字段：指数 | index_list | id (ts_code) | ts_code | 按 id | 无 |
| 4 | index_weight | 单字段：指数 | index_list | id (index_code) | index_code | 按 id | 无 |
| 5 | adj_factor_event | 单字段：股票 | stock_list | id (ts_code) | ts_code | 按 id | 多 API 合并，immediate 保存 |
| 6 | stock_klines | **多字段**：股票+周期 | stock_list × terms | id::term | ts_code + term | 按 id, term | 合并 job、按 term 过滤、immediate 保存 |

### 3.2 各维度的可能取值

| 维度 | 可能取值 | 说明 |
|------|----------|------|
| **实体列表来源** | `stock_list`, `index_list`, 其他（需 handler 注入） | dependencies 中的 key |
| **实体 ID 字段数** | 单字段 / 多字段 | 单字段：一只股票；多字段：一只股票的一个周期 |
| **Schema 侧标识** | `id`, `(id, term)` | DB 主键 / last_update 分组字段 |
| **API 侧参数名** | `ts_code`, `index_code`, `id`, `code` | 不同 API 用不同字段名传实体 ID |
| **列表是否展开** | 直接使用 / 展开为 list × terms | stock_klines 需要 stock_list × [daily,weekly,monthly] |

### 3.3 当前框架的推断点（需消除）

| 位置 | 推断逻辑 | 问题 |
|------|----------|------|
| `build_grouped_fetched_data` | 无 apis.group_by 时，依次尝试 ts_code, id, code, index_code | 不可靠，不同 API 可能冲突 |
| `compute_entity_date_ranges` (多字段) | terms 从 last_update_map 的 key 解析，或从 apis 名推断 (daily_kline→daily) | 依赖命名约定 |
| `handler_helper` 单字段 | 无 entity_key_field 时尝试 id, ts_code, code | 隐式兜底 |

---

## 四、语义化设计：统一 entity 配置

### 4.1 核心概念

用单一 `entity` 块描述「实体维度」的全部信息，不再分散在 result_group_by + apis.group_by。

```
entity = 谁 + 从哪里来 + 怎么标识（schema + API）
```

### 4.2 配置结构

```python
entity: {
    # 1. 实体列表来源
    "list": "stock_list",           # dependencies 中的 key，必填（per-entity 时）
    
    # 2. Schema 侧：DB 主键 / last_update 分组字段
    "key": "id",                     # 单字段
    # 或
    "keys": ["id", "term"],          # 多字段，与 key 互斥
    
    # 3. API 侧：请求参数中实体 ID 的字段名（显式，无推断）
    "param_key": "ts_code",          # 单字段时
    # 或
    "param_keys": ["ts_code", "term"],  # 多字段时，与 keys 一一对应
    
    # 4. 多字段专用：列表如何展开
    "terms": ["daily", "weekly", "monthly"],  # 仅当 keys 含 term 时
}
```

### 4.3 各用例的配置示例

#### 用例 1：corporate_finance（单字段，ts_code）

```python
"entity": {
    "list": "stock_list",
    "key": "id",
    "param_key": "ts_code",
}
```

#### 用例 2：stock_indicators（单字段，ts_code）

```python
"entity": {
    "list": "stock_list",
    "key": "id",
    "param_key": "ts_code",
}
```

#### 用例 3：index_klines（单字段，ts_code）

```python
"entity": {
    "list": "index_list",
    "key": "id",
    "param_key": "ts_code",
}
```

#### 用例 4：index_weight（单字段，index_code）

```python
"entity": {
    "list": "index_list",
    "key": "id",
    "param_key": "index_code",
}
```

#### 用例 5：adj_factor_event（单字段，ts_code）

```python
"entity": {
    "list": "stock_list",
    "key": "id",
    "param_key": "ts_code",
}
```

#### 用例 6：stock_klines（多字段，展开）

```python
"entity": {
    "list": "stock_list",
    "keys": ["id", "term"],
    "param_keys": ["ts_code", "term"],
    "terms": ["daily", "weekly", "monthly"],
}
```

### 4.4 无 entity 的场景（全局数据）

不配置 `entity` 即表示全局数据，无 per-entity 逻辑：

- `_get_entity_list()` 返回空
- last_update 查全表
- entity_date_ranges 仅 `_global`
- build_grouped 不触发，用 build_unified

---

## 五、配置与行为的映射（显式，无推断）

| 配置 | 行为 |
|------|------|
| `entity.list` | `_get_entity_list()` 从 `dependencies[list]` 取列表 |
| `entity.terms` | 有则展开：`[(e, t) for e in list for t in terms]` |
| `entity.key` | 单字段：从 entity_info 取 `entity_info[key]`；last_update 用 `[key]` 分组 |
| `entity.keys` | 多字段：从 entity_info 取复合值；last_update 用 keys 分组；entity_id 格式 `v1::v2` |
| `entity.param_key` | 单字段：`params[param_key]` 作为 entity_id 用于 fetched_data 分组 |
| `entity.param_keys` | 多字段：`"::".join(params[k] for k in param_keys)` 作为 entity_id |

### 5.1 可选：per-API 覆盖 param_key

当同一 handler 内不同 API 用不同参数名时：

```python
"entity": {
    "list": "index_list",
    "key": "id",
    "param_key": "ts_code",
    "param_key_overrides": {"index_weight": "index_code"}
}
```

优先级：`param_key_overrides[api_name]` > `param_key`。

---

## 六、框架行为清单（对照实现）

| 阶段 | 入口 | 使用配置 | 行为 |
|------|------|----------|------|
| 实体列表 | `_get_entity_list()` | entity.list, entity.terms | 从 deps[list] 取；有 terms 则展开 |
| last_update | `query_latest_date` | entity.key 或 keys → group_fields | 查表时按 group_fields 分组 |
| entity_date_ranges | `compute_entity_date_ranges` | entity.list, entity.key/keys, entity.terms | 遍历实体，计算每实体日期范围 |
| build jobs | `_build_jobs` | entity.key/keys, entity.list, entity.terms | 遍历 entity_list，匹配 entity_date_ranges |
| job payload | `on_build_job_payload` | entity.param_key/param_keys | 默认实现：从 entity_info 取 key，注入 params |
| fetched_data 分组 | `build_grouped_fetched_data` | entity.param_key/param_keys, param_key_overrides | 从 params 取 entity_id，无推断 |

---

## 七、默认实现与用户代码

### 7.1 默认行为（零配置）

- 无 `entity`：整个流程走 unified 模式，用户无需任何 entity 相关代码
- 有 `entity`：上述链路全部由配置驱动，默认 `on_build_job_payload` 按 param_key 注入

### 7.2 需要覆盖的场景

| 场景 | 原因 | 覆盖点 |
|------|------|--------|
| 少数 API 用不同 param 名 | 如 index_weight 用 index_code | 用 `param_key_overrides`，无需写 handler |
| 实体列表非 deps 标准 key | 如需从 ConfigManager 等读取 | 覆盖 `_get_entity_list()` |
| job 合并（如 stock_klines） | 同一股票多 term 合并为一个 bundle | 覆盖 `on_after_build_jobs` |

### 7.3 stock_klines 的简化

在 entity 配置正确后，stock_klines 可以：

1. 删除从 apis 名推断 terms 的逻辑，改用 `entity.terms`
2. 保留 `on_after_build_jobs` 的合并逻辑（业务需求：一股票多 term 打一个 bundle）
3. 其他交给默认实现

---

## 八、迁移与兼容

| 原配置 | 新配置 |
|--------|--------|
| `result_group_by.list` | `entity.list` |
| `result_group_by.key` | `entity.key` |
| `result_group_by.keys` | `entity.keys` |
| 无（推断） | `entity.param_key` |
| `apis[api].group_by` | `entity.param_key_overrides[api]` 或统一 `entity.param_key` |
| 无（推断） | `entity.terms`（多字段时必填） |

---

## 九、总结

1. **单一 entity 块**：list、key/keys、param_key/param_keys、terms、param_key_overrides
2. **无推断**：param_key 必填；多字段时 terms 必填
3. **大部分 handler**：仅配置，不写代码
4. **少数特殊**：通过 param_key_overrides 或 `_get_entity_list` / `on_after_build_jobs` 覆盖
