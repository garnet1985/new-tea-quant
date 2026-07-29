# Architecture — infra.cli

## 分层

```text
cli.py / devcli.py
        │
        ▼
   Cli (Facade)
   ├── user  → UserNamespace → UserBootstrap / UserRunner → user/*
   ├── dev   → DevNamespace  → DevRunner → dev/*
   └── shared → SharedNamespace（argv 展开）
```

- **user**：扫描、模拟、tag、renew、策略包、update/version；含 venv/install bootstrap。
- **dev**：UI、缓存清理、DuckDB checkpoint、pack、样本池、依赖检查。
- **shared**：短别名展开、`is_help_argv`、`aliases_for`；无业务 handler。

## 约束

- 对外只导出类 `Cli`；namespace 上均为 staticmethod。
- user / dev 各自维护 `SHORT_TO_LONG`（允许同短名不同语义，如 `ex`）。
- 实现包 `user/`、`dev/`、`shared/` 不作为公开 import 面。
