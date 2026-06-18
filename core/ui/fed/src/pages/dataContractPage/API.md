# Data Contract 列表 API（MVP）

只读目录，便于查找 **DataKey**。无 run / 编辑交互。

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
| `key` | string | `DataKey.value` |
| `display_name` | string | `DataSpec.display_name`，缺省为 key |
| `is_time_series` | boolean | `ContractType.TIME_SERIES` |
| `is_per_entity` | boolean | `ContractScope.PER_ENTITY` |
| `origin` | string | `system`（core `default_map`）或 `userspace`（userspace 扩展） |
| `is_custom` | boolean | `origin === "userspace"` |

**实现**：`core/modules/data_contract/launcher/contract_catalog.py` — 合并 `default_map` + userspace `discover_userspace_map()`，按 key 排序。
