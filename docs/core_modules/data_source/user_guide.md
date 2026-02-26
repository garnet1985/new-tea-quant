# Data Source · Userspace 使用指南

在 `userspace/data_source/` 下配置和扩展数据源，无需改 core。执行前保证 **mapping** 与各 Handler 的 **config** 已就绪。

---

## 目录结构

```
userspace/data_source/
├── mapping.py              # 必选：声明用哪个 Handler、是否启用、依赖
├── handlers/               # 各数据源执行器
│   └── <name>/             # 如 stock_list、stock_klines
│       ├── handler.py      # Handler 类（继承 BaseHandler）
│       ├── config.py       # CONFIG 字典：表名、save_mode、apis 等
│       └── schema.py       # 可选，自定义 Schema 时
└── providers/              # 第三方 API 封装
    └── <name>/             # 如 tushare、akshare
        ├── provider.py     # Provider 类（继承 BaseProvider）
        └── auth_token.txt  # 可选，需要 token 时（勿提交）
```

---

## mapping.py

在 `DATA_SOURCES` 里为每个数据源配置：

| 项 | 说明 |
|----|------|
| `handler` | `"<目录名>.<类名>"`，如 `"stock_list.TushareStockListHandler"`，对应 `handlers/<目录名>/handler.py` 中的类 |
| `is_enabled` | 是否参与执行，`True` / `False` |
| `depends_on` | 可选。依赖的其他 data source key 或保留依赖，如 `["stock_list", "latest_trading_date"]` |

**保留依赖**（由框架注入，不能作为 data source key 使用）：如 `latest_trading_date`。完整列表见 `core.modules.data_source.reserved_dependencies.RESERVED_DEPENDENCY_KEYS`。

示例：

```python
DATA_SOURCES = {
    "stock_list": {
        "handler": "stock_list.TushareStockListHandler",
        "is_enabled": True,
    },
    "stock_klines": {
        "handler": "stock_klines.KlineHandler",
        "is_enabled": True,
        "depends_on": ["stock_list", "latest_trading_date"],
    },
}
```

---

## 新增 / 修改 Handler

1. 在 `handlers/` 下建目录，如 `handlers/my_data/`。
2. **handler.py**：写一个继承 `BaseHandler` 的类，实现生命周期钩子（如 `on_before_run`、`on_after_mapping`、`on_before_save`）或按基类约定组织 ApiJob。类名与 mapping 中的 `"<目录名>.<类名>"` 一致。
3. **config.py**：定义 `CONFIG`，至少包含 `table`、`save_mode`、`apis`（或你 Handler 使用的配置结构）。框架会把 CONFIG 注入到 `context["config"]`。
4. 在 **mapping.py** 增加一项：`"my_data": { "handler": "my_data.MyDataHandler", "is_enabled": True, "depends_on": [...] }`。

具体可覆盖的钩子与 ApiJob 写法见 [api.md](./api.md) 与 [architecture.md](./architecture.md)。

---

## 新增 Provider

1. 在 `providers/` 下建目录，如 `providers/my_api/`。
2. **provider.py**：写一个继承 `BaseProvider` 的类，定义 `provider_name`、`requires_auth`、`auth_type`（如需）、`api_limits`（各方法每分钟调用上限），并实现 `_initialize()` 和对外 API 方法。
3. 需要 token 时：同目录放 `auth_token.txt`（一行 token）或用环境变量（由 Provider 在 `_initialize` 里读取）。不要把 `auth_token.txt` 提交到版本库。

框架会从 userspace 发现并注册 Provider，Handler 的 config 里通过 `provider_name` 指定使用哪个 Provider。

---

## 运行

```python
from core.modules.data_source.data_source_manager import DataSourceManager

manager = DataSourceManager(is_verbose=True)
manager.execute()   # 执行所有 is_enabled 的数据源
```

是否写库由各 Handler 的 config 里 `is_dry_run` 等控制。更多入口（如按日期续跑、单 Handler 测试）见 [api.md](./api.md)。

---

## 相关文档

- [API 文档](./api.md) — 类与方法说明  
- [架构说明](./architecture.md) — 设计与流程  
- [概览](./overview.md) — 概念与用法概览  
