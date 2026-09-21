# TODO：安装失败 Trace 要能排障

**状态：** 待做（2026-09-12 记下）。不在决策者第一刀里。  
**触发：** 远端 `install.complete` 只有 `success=false`、`entry=cli`、`error_code=step_failed:import_data`。机器画像有（Windows / py3.13 / 12GB / duckdb），**没有**失败表、异常类型、是否锁文件。用户联系不到，无法复现。

现行 `SetupTrace.install_complete` 故意只传稳定 step id，「never exception text」（见 `core/trace_events.py`）。步级码不够用。

## 要加的字段（脱敏，仍禁止路径 / token / 用户目录）

失败时在 `install.complete`（或同一次 `install.step_failed`）带上：

| 字段 | 用途 |
|------|------|
| `failed_step` | 已有，如 `import_data` |
| `exc_type` | `RuntimeError` / `OSError` / DuckDB 锁相关类名 |
| `failed_table` | 当时 `in_progress_table` 或 `部分表导入失败` 列表里的逻辑表名 |
| `error_class` | 粗分：`lock` / `bad_zip` / `multi_zip` / `empty_archive` / `db_unavailable` / `table_import` / `interrupt` / `other` |
| `message_safe` | 截断、去路径后的短文案；去掉 traceback 栈帧，优先保留末尾异常行 |

可选：zip 个数、是否 `force`、导入已完成表数 / 总表数。

## 不要

- 完整 traceback、绝对路径、SQL 原文、数据包文件名若可能含用户路径
- 为了隐私把失败原因整段扔掉——现在就是这个问题

## 落点

- `infra.setup`：`cli_runtime` / `ui_runtime` / `SetupDataInstaller` 在 raise 前把结构化原因交给 `SetupTrace`
- `infra.trace`：确认 sanitize 允许这些 key；必要时加 `error_class` 白名单
