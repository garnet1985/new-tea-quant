# Tag 控制台 API（T1）

本文档描述 Tag 列表与运行（MVP）的 BFF 契约。实现编排见 `core/bff/APIs/tag/ROUTES_ORCHESTRATION.md`。

## HTTP 前缀

- BFF 蓝图前缀 **`/api`**（`core/bff/app.py`）。
- 下文路径省略 `/api` 时，完整 URL 仍为 **`/api/v1/...`**。
- **「T1-xx」** 为本契约接口族编号；路径中的 **`/v1/`** 为 REST 版本段。

## 核心模型

- **`tag_key`**：相对 `userspace/extensions/tags` 根的 POSIX 路径（与 discovery / CLI `--scenario` 一致），如 `demo/market_cap_tier`。
- **`name`**：列表与 run 接口中的稳定 ID，**等于 `tag_key`**（对齐 strategy 列表的 `name` 字段）。
- **`display_name`**：展示用，来自 settings `meta.display_name`；缺省为空字符串，FED 回退为 `name`。
- **运行（run）**：异步 job；**不是**持久化实体。MVP **不提供** run 历史列表。

### BFF 边界

- BFF **不做** tag 业务缓存决策；是否 incremental、是否写库由 **`Tag` / 引擎**（含 settings `is_dry_run`）决定。
- BFF 职责：HTTP 校验、调用 **`TagCatalog` / `TagRunLauncher`**（BFF helpers / runner 薄壳；进度经 core `TagRunProgress`）、维护 **单进程 tag run 编排**，统一 `ok` / `error` 信封。

## API 清单（T1 — MVP）

| 编号 | 方法 | 路径 | 用途 |
|------|------|------|------|
| T1-00 | GET | `/runtime/pipeline` | 全局 pipeline 是否 busy（DuckDB 互斥；跨 tag/strategy/renew） |
| T1-01 | GET | `/tags/list` | 分页 Tag scenario 列表 |
| T1-02 | POST | `/tag/<path:tag_key>/run` | 启动单 scenario 计算 |
| T1-03 | GET | `/tag/<path:tag_key>/run/progress` | 轮询 run 进度 |

**MVP 未注册**：单 scenario 详情 GET、settings 保存、运行全部、tag 值预览。

### 并发（两层）

| 层 | 机制 | HTTP |
|----|------|------|
| Tag ↔ Tag | BFF tag run 锁；FED 跑一个 disable 其余 | T1-02 重复 → **409** |
| 全局 pipeline | `.ntq/runtime/pipeline_active.json` 租约 | T1-00 `busy`；T1-02 冲突 → **409** |

FED 建议：进 `/tags` 调 T1-00；任一 tag 运行中再调 T1-03；全局 `busy && kind !== tag_run` 时 disable 所有运行按钮。

## 固定约定

### 响应信封

成功：

```json
{
  "status": "ok",
  "message": { }
}
```

失败：

```json
{
  "status": "error",
  "message": {
    "detail": "人类可读说明",
    "code": "可选机器码"
  }
}
```

与 strategy / scan BFF 一致（`core/bff/shared/response.py`）。

### 分页（T1-01）

- Query：`page`（1-based，默认 `1`）、`limit`（默认 `20`，上限 `100`）。
- 响应 `message`：`items`、`total`、`page`、`limit`。
- 排序：按 `name`（`tag_key`）字典序升序。

### `tag_key` 路径段

- 与 strategy 的 `<path:strategy_name>` 相同：可含 `/`，须 URL 编码。
- body **不得**用另一 `tag_key` 覆盖路径（若 body 含校验字段，须与路径一致，否则 **400**）。

---

## 契约细则

### T1-00 `GET /runtime/pipeline`

**语义**：返回当前是否已有**占用 DuckDB 相关域**的长任务（单 BFF 进程内协调；文件租约供多入口只读查询）。

**成功 `message`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `busy` | boolean | 是否有活跃租约 |
| `kind` | string \| null | `tag_run` \| `strategy_scan` \| `strategy_run` \| `data_renew` \| null |
| `job_id` | string \| null | 活跃 job |
| `resource_key` | string \| null | 如 `demo/market_cap_tier`、strategy name、data source key |
| `label` | string \| null | 可选展示文案 |
| `domains` | string[] | 占用的 storage domain，如 `["data","tag"]` |
| `started_at` | string \| null | ISO8601 |

**空闲示例**

```json
{
  "status": "ok",
  "message": {
    "busy": false,
    "kind": null,
    "job_id": null,
    "resource_key": null,
    "label": null,
    "domains": [],
    "started_at": null
  }
}
```

**实现**：`core/infra/system_actions/core/cache_cleanup/pipeline_lease.py`；Tag MVP 至少写入/释放 `kind=tag_run`；Strategy scan/run、renew 后续接入同一 acquire/release。

---

### T1-01 `GET /tags/list`

**语义**：返回 userspace 下通过 discovery 发现的 scenario 摘要（`TagCatalog.fetch_page`），并合并 tag DB 侧可选元数据（最后计算日期等）。

**Query**

| 参数 | 必填 | 说明 |
|------|------|------|
| `page` | 否 | 默认 `1` |
| `limit` | 否 | 默认 `20`，最大 `100` |

**`message.items[]` 元素**

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | **= `tag_key`** |
| `display_name` | string | `meta.display_name` |
| `is_enabled` | boolean | settings 顶层 `is_enabled` |
| `description` | string | `meta.description`，可空 |
| `tag_definitions` | array | settings `tags[]` 摘要，见下表 |
| `last_computed_as_of` | string \| null | **列表「最后更新」主字段**：`sys_tag_value` 上该 scenario 的 **MAX(as_of_date)**，统一 **8 位 `YYYYMMDD`**；从未计算为 `null`（见 `tag_service.get_max_as_of_date`） |
| `scenario_updated_at` | string \| null | `sys_tag_scenario.updated_at`（ISO）；**仅元数据/registry 变更**，增量计算不写；DuckDB 下常等于创建时间，勿当作计算完成时间 |
| `execution_mode` | string | `calculation.execution_mode` 规范化值（如 `entity_timeline`、`calendar_slice`）；仅展示，MVP 不可改 |
| `update_mode` | string | `calculation.update_mode`：`incremental` \| `refresh`（默认 `incremental`） |
| `recompute` | boolean | `calculation.recompute`；为 true 时本次运行会强制重算（与 refresh 语义相关） |

**`tag_definitions[]` 元素**

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | `tags[].name` |
| `display_name` | string | `tags[].display_name`，缺省回退 `name` |

**示例**

```json
{
  "status": "ok",
  "message": {
    "items": [
      {
        "name": "demo/market_cap_tier",
        "display_name": "市值档位",
        "is_enabled": true,
        "description": "基于 total_market_value 划分档位…",
        "tag_definitions": [
          { "name": "market_cap_tier", "display_name": "市值档位" }
        ],
        "last_computed_as_of": "20250601",
        "execution_mode": "entity_timeline",
        "update_mode": "incremental",
        "recompute": true
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20
  }
}
```

**错误**

- discovery 根目录不存在：`items: []`、`total: 0`、**200**（与 strategy 列表空集一致）。
- 内部异常：**500**。

---

### T1-02 `POST /tag/<path:tag_key>/run`

**语义**：在后台启动 **单个** scenario 的 `Tag().execute(scenario_name=tag_key)`（经 `TagRunLauncher.trigger`）。MVP **不支持** body 内联 settings。

**请求体**

- 可为空 `{}`，或省略 body。
- **不允许** MVP 通过 body 传入完整 settings 覆盖磁盘配置。

**成功响应 `message`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_triggered` | boolean | 固定 `true` |
| `job_id` | string | 轮询键 |
| `run_id` | string | 与 `job_id` 相同（别名，对齐 strategy V2-05） |
| `tag_key` | string | 回显路径参数 |
| `name` | string | 与 `tag_key` 相同（对齐 FED 列表 `id`） |

**失败**

| HTTP | 条件 |
|------|------|
| **400** | `tag_key` 无效、未 discovered、或 `is_enabled=false` |
| **409** | 已有 tag run（第 1 层），或全局 pipeline 租约被占用（第 2 层，见 T1-00） |
| **500** | 启动线程/写 progress 种子失败 |

失败 `message` 示例：

```json
{
  "status": "error",
  "message": {
    "detail": "已有 Tag 任务在运行中，请稍后重试"
  }
}
```

**成功示例**

```json
{
  "status": "ok",
  "message": {
    "is_triggered": true,
    "job_id": "tag-run-a1b2c3d4",
    "run_id": "tag-run-a1b2c3d4",
    "tag_key": "demo/market_cap_tier",
    "name": "demo/market_cap_tier"
  }
}
```

---

### T1-03 `GET /tag/<path:tag_key>/run/progress`

**语义**：读取 **T1-02** 对应 job 的进度；**只读**，不触发计算。

**Query**

| 参数 | 必填 | 说明 |
|------|------|------|
| `job_id` | **是** | T1-02 返回的 `job_id` |

**成功响应 `message`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `job_id` | string | 与 query 一致 |
| `run_id` | string | 同 `job_id` |
| `tag_key` | string | 必须与路径一致，否则 **404** |
| `progress` | number | 0～100，保留两位小数 |
| `status` | string | `running` \| `completed` \| `failed` |
| `phase` | string | 可选；`queued` \| `running` \| `completed` \| `failed`（与 scan 对齐） |
| `label` | string | 可选；人类可读阶段文案（如「分发任务 12/48」） |
| `is_success` | boolean | 仅 `status=completed` 时为 `true`；`failed` 为 `false` |
| `reason` | string | 仅 `failed` 时 |

**轮询约定**

- FED 在 `status` 为 `running`（或 `phase` 非终态）时重复请求；间隔建议 1～2s。
- `progress >= 100` 且 `status=completed` 时停止；可刷新 T1-01 列表以更新 `last_computed_as_of`。
- 进度文件/任务不存在、或 `job_id` 与 `tag_key` 不匹配 → **404**。

**运行中示例**

```json
{
  "status": "ok",
  "message": {
    "job_id": "tag-run-a1b2c3d4",
    "run_id": "tag-run-a1b2c3d4",
    "tag_key": "demo/market_cap_tier",
    "progress": 42.5,
    "status": "running",
    "phase": "running",
    "label": "执行计算 17/40"
  }
}
```

**完成示例**

```json
{
  "status": "ok",
  "message": {
    "job_id": "tag-run-a1b2c3d4",
    "run_id": "tag-run-a1b2c3d4",
    "tag_key": "demo/market_cap_tier",
    "progress": 100.0,
    "status": "completed",
    "phase": "completed",
    "is_success": true
  }
}
```

---

## FED 对接备忘

- 列表展示名：`display_name || name`（可抽 `getTagDisplayLabel(item)`，对齐 `getStrategyDisplayLabel`）。
- URL 编码：`tag_key.split('/').map(encodeURIComponent).join('/')`。
- `is_enabled=false`：展示行，**禁用**运行按钮 + tooltip。
- MVP **无**详情页；运行按钮在列表行内。
- API 客户端建议路径：`core/ui/fed/src/api/apis/tagApi.js`（待建）。

## 后续迭代（非 MVP，预留编号）

| 编号 | 方法 | 路径 | 说明 |
|------|------|------|------|
| T1-04 | GET | `/tag/<path:tag_key>/version/latest` | 单 scenario 快照 / 可读 settings 摘要 |
| T1-05 | POST | `/tag/<path:tag_key>/apply-settings/...` | 写回 settings.py |
| T1-06 | GET | `/tag/<path:tag_key>/values/preview` | tag-preview 页 |

Data Source 契约见 [`../dataSourcePage/API.md`](../dataSourcePage/API.md)（T2-xx）。
