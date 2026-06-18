# Data Source 列表 API（Phase A）

只读目录 + 更新按钮占位（Token 未配置时禁用；更新执行下一版接入）。

## HTTP 前缀

同 Tag：`/api/v1/...`。

## DS-01 `GET /api/v1/data-sources/list`

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
| `data_end` | object | 全系统数据截至日（见下） |

**`data_end`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `configured_as_of` | string \| null | `data.json` 的 `as_of_latest_completed_trading_date` |
| `effective_end_date` | string \| null | 实际用于评估的截至日（YYYYMMDD） |
| `is_end_date_truncated` | boolean | 是否配置了 as-of 截断 |
| `truncation_hint` | string | 截断时 UI 提示文案 |
| `truncation_settings_path` | string \| null | 截断时跳转设置内页路径（如 `/settings/data`） |

**`items[]` 元素**

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | data source key |
| `display_name` | string | 中文展示名 |
| `target_table` | string | handler config `table` |
| `providers` / `providers_label` | | Provider 列表 |
| `renew_type` / `renew_type_label` | | 更新方式（增量/滚动/全量刷新） |
| `renew_interval_days` | number \| null | 更新间隔天数 |
| `rate_limit_per_minute` | number \| null | API 限速最小值 |
| `requires_auth` / `auth_ready` / `auth_hint` | | Token 状态 |
| `can_renew` | boolean | 是否可点击更新（Token 就绪） |
| `update_status` | string | `needs_update` / `up_to_date` |
| `update_status_label` | string | `需要更新` / `已经更新` |
| `update_status_hint` | string | 可选补充说明 |
| `origin` / `is_custom` | | 系统 / 自定义 |

**实现**：`core/modules/data_source/launcher/source_catalog.py` + `catalog/freshness_probe.py`

---

## 后续（Phase B）

| 编号 | 方法 | 路径 | 用途 |
|------|------|------|------|
| DS-02 | POST | `/data-source/<source_key>/renew` | 单行更新 + 进度 |
| DS-03 | POST | `/data-sources/renew` | 全部更新 |
| DS-04 | GET | `/data-source/renew/progress` | 轮询进度 |
