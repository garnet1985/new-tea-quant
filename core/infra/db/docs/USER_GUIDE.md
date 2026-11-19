# Database — 用户指南

**模块：** `infra.db` · **版本：** `0.3.2`

**最低支持核心版本：** `>=0.5.0`

数据库底层——按配置挂后端（DuckDB / PostgreSQL / MySQL），管建表和迁移。  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 你存在本地的行情、策略、标签数据，都经它读写到数据库里
- 默认用 DuckDB（本地文件，零安装），也能切到 PostgreSQL / MySQL
- 应用升级时自动跑表结构迁移，保证旧数据还能用

## 配置说明

配置文件：默认在 `core/default_config/database/`，用户覆盖放 `userspace/system/config/`。

| 配项 | 在哪配 | 默认值 | 说明 |
|------|--------|--------|------|
| `database_type` | `database/common.json` | `duckdb` | 用哪个数据库引擎：`duckdb` / `postgresql` / `mysql` |
| 连接信息 | `database/postgresql.json` 等 | 见文件 | 用 PostgreSQL / MySQL 时填地址、账号、密码 |
| `batch_write` | `database/common.json` | 开启 | 批量写入的批次大小和落盘间隔，一般不用动 |

DuckDB 的数据文件在 `userspace/system/db/` 下。

## 常见使用方式

### 场景 1：默认使用（大多数人）

1. 什么都不用配，装好就是 DuckDB
2. 数据自动存在本机 `userspace/system/db/` 下

### 场景 2：切换到 PostgreSQL / MySQL

1. 在 `userspace/system/config/` 里改 `database_type`
2. 填好对应引擎的连接信息
3. 重启应用，让它跑一遍建表和迁移
4. 确认数据读写正常后再删掉旧的 DuckDB 文件（如需）

### 场景 3：应用升级后打不开数据

1. 先看启动日志里有没有迁移报错
2. 有报错先备份数据库文件再求助，别反复重试

## 常见坑与注意事项

- **改了数据库引擎忘了跑迁移**：新库是空的，看起来像"数据丢了"。其实旧数据还在原引擎里，切回去或完成迁移即可
- **DuckDB 文件被另一进程占用**：报锁 / IO 错误。同一时间只能开一个实例，先关掉另一个再启动
- **直接手动改 DuckDB 文件**：容易写坏，请通过应用操作数据
- 删除 `userspace/system/db/` 等于清空全部本地数据，删前先备份

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
