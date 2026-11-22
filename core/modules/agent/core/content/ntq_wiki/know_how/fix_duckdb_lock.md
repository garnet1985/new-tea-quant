---
title: fix duckdb lock 清理 DuckDB 文件占用
aliases:
  - duckdb lock
  - Conflicting lock
  - 文件被其他进程占用
  - 无法打开 DuckDB
  - duckdb_file_locks
summary: DuckDB 同时只能一个写进程；用助手工具或 Python API 列出并结束占用进程。
---

# 如何清理 DuckDB 文件占用

报错类似：

- `无法打开 DuckDB（文件被其他进程占用）`
- `Conflicting lock is held in ... Python`

说明另一个进程正开着 `userspace/system/db/*.duckdb`（常见：未退出的 `python -c`、卡死的 CLI，或仍在跑的 launcher）。

## 助手工具（推荐）

对 AI 助手说「DuckDB 被占用了，帮我清理」，或直接调工具：

1. **先列出**：`duckdb_file_locks`（不要带 `kill`）
2. **再清理卡死进程**：`duckdb_file_locks`，参数 `kill=true`
3. **确认可关界面时**才加 `force=true`（会结束 launcher / BFF）

工具**不会**删库或删 `.wal`。

## Python API

```python
from core.infra.db import Db

Db.duckdb.inspect_file_locks()
Db.duckdb.release_file_locks(kill=True)           # 清卡死 Python
Db.duckdb.release_file_locks(kill=True, force=True)  # 连 launcher 一起
```

## 注意

- 同一文件同时只能一个写连接；开着 launcher 时其它进程也会抢锁。
- 系统 `fileprovider` 等索引进程可能出现在列表里，工具不会杀它们。
- 若仍打不开：确认没有第二个 NTQ 窗口，再重启本机相关 Python 进程。

相关：[切换数据库](switch_database.md) · [数据基建](../wiki/data_infrastructure.md)
