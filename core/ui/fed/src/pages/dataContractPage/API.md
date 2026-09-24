# Data Contract 列表 API（MVP）

目录浏览 + 重新发现。便于查找 **DataKey**；新增 userspace 契约后可热加载，无需重启 NTQ。

## DC-01 `GET /api/v1/data-contracts/list`

| Query | 说明 |
|-------|------|
| `page` | 1-based，默认 1 |
| `limit` | 默认由 BFF pagination helper 决定 |

**Response `message`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `items[]` | array | 当前页 |
| `total` | number | 全量条数 |
| `page` / `limit` | number | 回显 |

**`items[]` 元素**

| 字段 | 类型 | 来源 |
|------|------|------|
| `key` | string | DataKey |
| `display_name` | string | declaration `meta.display_name`，缺省为 key |
| `is_time_series` | boolean | `ContractType.TIME_SERIES` |
| `is_per_entity` | boolean | `ContractScope.PER_ENTITY` |
| `origin` | string | `system` 或 `userspace` |
| `is_custom` | boolean | `origin === "userspace"` |

## DC-02 `POST /api/v1/data-contracts/reload`

强制 `ContractIssuer.reload()`（清类级缓存、重读 userspace 模块），再返回与 list 相同形状的目录页。

| Query | 说明 |
|-------|------|
| `page` / `limit` | 同 list，用于回传刷新后的分页结果 |

**Response `message`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `reloaded` | boolean | 恒为 `true` |
| `total` | number | 发现后的全量条数 |
| `items[]` | array | 当前页（字段同 DC-01） |
| `page` / `limit` | number | 回显 |

**实现**：`core/bff/APIs/data/contracts/helpers/contract_catalog.py`
