# Data Source 模块重构设计文档

## 一、目标

1. **禁止推断**：框架不做任何隐式猜测，所有行为由配置显式声明
2. **用户代码简单**：大部分 handler 使用默认实现，零或极少量覆盖
3. **语义清晰**：配置命名接地气，配置与行为一一对应

---

## 二、核心概念：两种 Group By

| 场景 | 作用 | 配置驱动 |
|------|------|----------|
| **Job 合并** | 按维度合并 jobs，提高请求效率 | `job_execution.merge` |
| **Fetched data 分组** | 重组抓取结果为 `{api_name: {entity_id: result}}` | `params_mapping`（派生） |

合并与拆分是互逆操作：合并 jobs 后，处理时自然按 bundle 内每个 API 拆分结果。

---

## 三、配置结构

### 3.1 job_execution（renew 下）

```python
"renew": {
    "type": "incremental",
    "last_update_info": {...},
    "job_execution": {
        "list": "stock_list",           # 实体列表来源，dependencies 的 key
        "key": "id",                    # 单字段（与 keys 二选一）
        # 或
        "keys": ["id", "term"],         # 多字段
        "terms": ["daily", "weekly", "monthly"],  # 多字段时，展开 list × terms
        "merge": {
            "by": "id"                  # 按此字段合并 jobs，不配置则不合并
        }
    }
}
```

**per entity 判断**：有 `job_execution` 即 per entity；无则为全局模式。

### 3.2 apis 配置：params_mapping + result_mapping

```python
"apis": {
    "daily_kline": {
        "provider_name": "tushare",
        "method": "get_daily_kline",
        "max_per_minute": 700,
        "params_mapping": {
            "ts_code": "id",
            "term": "term",
        },
        "result_mapping": {
            "id": "ts_code",
            "date": "trade_date",
            ...
        },
    },
}
```

| 配置 | 方向 | 含义 |
|------|------|------|
| **params_mapping** | entity → request | `params[api_param] = entity_info[entity_field]`，经 `to_provider_id` 转换 |
| **result_mapping** | response → schema | `record[schema_field] = raw[api_field]`（原 field_mapping 重命名） |

### 3.3 钩子：to_provider_id

```python
def to_provider_id(self, entity_id: str, api_name: str, context: Dict) -> str:
    """将系统 entity_id 转为该 API 所需的 provider 格式。默认原样返回。"""
    return entity_id
```

当 API 需要不同格式（如 EastMoney 的 secid）时，子类覆盖此方法。

---

## 四、各 Handler 配置示例

### 4.1 stock_klines（多字段 + 合并）

```python
"job_execution": {
    "list": "stock_list",
    "keys": ["id", "term"],
    "terms": ["daily", "weekly", "monthly"],
    "merge": {"by": "id"},
}
# apis: params_mapping {"ts_code": "id", "term": "term"}, result_mapping {...}
```

### 4.2 corporate_finance / stock_indicators / adj_factor_event（单字段，不合并）

```python
"job_execution": {
    "list": "stock_list",
    "key": "id",
}
# params_mapping: {"ts_code": "id"}
```

### 4.3 index_klines（单字段，不合并）

```python
"job_execution": {
    "list": "index_list",
    "key": "id",
}
# params_mapping: {"ts_code": "id"}
```

### 4.4 index_weight（单字段，不同 param 名）

```python
"job_execution": {
    "list": "index_list",
    "key": "id",
}
# params_mapping: {"index_code": "id"}
```

### 4.5 adj_factor_event（qfq_kline 需 secid 转换）

```python
# adj_factor, daily_kline: params_mapping {"ts_code": "id"}
# qfq_kline: params_mapping {"secid": "id"}
# Handler 覆盖 to_provider_id，当 api_name=="qfq_kline" 时返回 convert_to_eastmoney_secid(entity_id)
```

### 4.6 全局数据（stock_list, gdp, cpi, lpr 等）

不配置 `job_execution`，无 `params_mapping`（或仅固定 params）。

---

## 五、配置与行为映射

| 配置 | 行为 |
|------|------|
| `job_execution.list` | `_get_entity_list()` 从 `dependencies[list]` 取 |
| `job_execution.terms` | 有则展开：`[(e, t) for e in list for t in terms]` |
| `job_execution.key` / `keys` | last_update 分组、entity_date_ranges、build jobs |
| `job_execution.merge.by` | 框架按此字段合并 jobs |
| `params_mapping` | 注入 params + fetched_data 分组（从 params 取 entity_id） |
| `result_mapping` | 响应字段映射 |
| `to_provider_id` | entity_id 注入前转换（默认原样） |

**Fetched data 分组**：由 `params_mapping` 的 param 名派生，无需单独配置。

---

## 六、框架改动

### 6.1 移除 / 替换

| 当前 | 新 |
|------|-----|
| `result_group_by` | `job_execution` |
| `get_group_by()`, `get_group_by_key()`, `get_group_fields()` | 直接读 `job_execution` |
| `has_result_group_by()`, `is_per_entity()` | `job_execution is not None` |
| `apis.group_by` | `params_mapping` |
| `field_mapping` | `result_mapping` |
| 推断 ts_code/id/code/index_code | 无，用 params_mapping |
| 推断 terms | 用 `job_execution.terms` |

### 6.2 新增

- 默认 `on_build_job_payload`：按 `params_mapping` 注入，经 `to_provider_id` 转换
- 默认 job 合并：`job_execution.merge.by` 时框架合并
- `build_grouped_fetched_data`：从 `params_mapping` 的 key 取 entity_id

### 6.3 不变

- `dependencies` 结构不变（stock_list, index_list 等）
- last_update、entity_date_ranges 逻辑不变，仅配置来源改为 job_execution

---

## 七、Handler 改动

| Handler | 可移除 | 需保留 |
|---------|--------|--------|
| corporate_finance | on_build_job_payload | — |
| index_klines | on_build_job_payload | — |
| stock_klines | on_build_job_payload, on_after_build_jobs 合并逻辑 | on_after_single_api_job_bundle_complete（immediate 保存） |
| adj_factor_event | on_build_job_payload 大部分 | to_provider_id 覆盖 |
| stock_indicators | on_before_fetch 扩展 | 改为标准 flow |
| index_weight | on_before_fetch 扩展 | 改为标准 flow |

---

## 八、迁移对照表

| 原配置 | 新配置 |
|--------|--------|
| `result_group_by.list` | `job_execution.list` |
| `result_group_by.key` | `job_execution.key` |
| `result_group_by.keys` | `job_execution.keys` |
| 无 | `job_execution.terms`（多字段时） |
| 无 | `job_execution.merge.by`（需合并时） |
| 无 | `apis[].params_mapping` |
| `apis[].group_by` | 合并进 `params_mapping` |
| `apis[].field_mapping` | `apis[].result_mapping` |

---

## 九、实施顺序建议

1. 更新 config 访问层（job_execution 读取，兼容 result_group_by）
2. 实现 params_mapping 注入与 to_provider_id 钩子
3. 实现 job_execution.merge 的框架合并逻辑
4. 移除推断，build_grouped_fetched_data 改用 params_mapping
5. 迁移各 handler 配置
6. 删除废弃代码（result_group_by、apis.group_by 等）
