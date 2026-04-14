# Config · Userspace 使用指南

用 `userspace/config/` 覆盖或补充框架默认配置，无需改 `core/default_config/`。实际生效 = 默认配置 + 用户配置（深度合并）+ 环境变量覆盖。只写你要改的部分即可。

---

## 目录结构

```
userspace/config/                  # 用户配置（可选）
├── data.json                      # 数据相关（开始日期、小数位、股票过滤等）
├── market.json                    # 市场配置
├── system.json                    # 系统配置
├── worker.json                    # Worker 并发等
├── logging.json                   # 日志
└── database/
    ├── common.json                # 公共项（如 database_type）
    ├── postgresql.json            # PostgreSQL（通常只写 user/password）
    ├── mysql.json
    └── sqlite.json
```

**约定**：文件名与 `core/default_config/` 一一对应；缺文件则该项完全使用默认值。敏感信息可用环境变量，勿把含密码的 JSON 提交到版本库。

---

## 常用覆盖示例

**数据库（PostgreSQL）**：只写需要覆盖的字段，其余继承默认。

```json
// userspace/config/database/postgresql.json
{
  "user": "my_user",
  "password": "my_password"
}
```

或用环境变量：`DB_POSTGRESQL_USER`、`DB_POSTGRESQL_PASSWORD` 等（由配置管理组件读取）。

**切换数据库类型**：

```json
// userspace/config/database/common.json
{ "database_type": "mysql" }
```

再在 `userspace/config/database/mysql.json` 里写 MySQL 的 user/password 等。

**股票过滤**（只覆盖过滤规则）：

```json
// userspace/config/data.json
{
  "stock_list_filter": {
    "exclude_patterns": {
      "start_with": { "id": ["688", "8"] }
    }
  }
}
```

**Worker 并发**：在 `worker.json` 中按需覆盖 `default_task_config`、`module_task_config` 等（参见 `core/default_config/worker.json` 结构）。

---

## 代码里如何读配置

不直接读 JSON。通过 Project Context 的配置管理组件读取，例如：

- `ConfigManager.load_database_config()`、`ConfigManager.load_data_config()`、`ConfigManager.load_worker_config()` 等；
- 或 `ProjectContextManager().config.load_with_defaults(default_path, user_path, ...)`。

详见 [`core/infra/project_context/docs/API.md`](../../core/infra/project_context/docs/API.md) 与 [`ARCHITECTURE.md`](../../core/infra/project_context/docs/ARCHITECTURE.md)。

---

## 相关文档

- [Config 概览](./overview.md)
- [Config 架构](./architecture.md)
- [Project Context 配置管理](../../core/infra/project_context/docs/API.md)
