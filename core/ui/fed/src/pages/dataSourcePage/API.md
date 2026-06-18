# Data Source 控制台 API（T2 — 草案）

**状态**：Phase 2，Tag MVP 完成后再实现。编号与 [`../tagPage/API.md`](../tagPage/API.md) 并列。

## HTTP 前缀

同 Tag：`/api/v1/...`。

## API 清单（草案）

| 编号 | 方法 | 路径 | 用途 |
|------|------|------|------|
| T2-01 | GET | `/data-sources/list` | 已配置 data source 列表（只读） |
| T2-02 | POST | `/data-source/<source_key>/renew` | 触发单 source renew |
| T2-03 | POST | `/data-sources/renew` | 触发全部 enabled renew（可选 query `force=0\|1`） |
| T2-04 | GET | `/data-source/renew/progress` | 轮询 renew job（query `job_id`） |

## T2-01 列表项（草案字段）

| 字段 | 说明 |
|------|------|
| `name` | data source key（如 `stock_klines`） |
| `is_enabled` | mapping 中 `is_enabled` |
| `depends_on` | string[] |
| `target_table` | handler config `table` |
| `last_renewed_at` | 可选；自 DB / cache 推导，无则 `null` |

## T2-02 / T2-03 运行

- 成功：`is_triggered`、`job_id`、`run_id`（与 T1-02 / scan 同形）。
- 已有 renew 或 DuckDB 互斥：**409**。
- `force=true`：对齐 CLI `renew --force`（实现阶段落实 query 或 body）。

## T2-04 进度

- 响应字段对齐 **T1-03** / scan progress：`progress`、`status`、`label`、`is_success`、`reason`。
- 全局单 job：同一时刻仅一个 renew 编排（含「全部 renew」）。

---

实现编排占位：`core/ui/bff/APIs/data_source/ROUTES_ORCHESTRATION.md`（待建）。
