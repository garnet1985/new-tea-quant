# Data Source 设计说明

**版本：** `0.2.0`

本文档描述 **userspace 配置布局**、**schema 来源**与 **handler 发现规则**。实现以 `data_source_manager.py`、`service/manager_helper.py` 为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## userspace 布局

| 路径 | 作用 |
| --- | --- |
| `userspace/data_source/mapping.py` | 定义 **`DATA_SOURCES`**（或兼容 `mapping.json` 的发现逻辑，见 `DataSourceManagerHelper`） |
| `userspace/data_source/handlers/<name>/config.py` | 各数据源 **`CONFIG`**（顶层 **`table`** 绑定物理表名） |
| `userspace/data_source/handlers/.../handler.py`（或 mapping 指向的模块） | **Handler** 类实现 |
| `userspace/data_source/providers/` | **Provider** 包，供 `ClassDiscovery` 扫描 |

---

## Schema 与表绑定

- **`DataSourceConfig`** 顶层 **`table`** → **`DataManager.get_table(table_name)`** → **`model.load_schema()`** 得到 **dict schema**。
- Handler 输出需与该 schema 对齐；**不写独立 schema 文件**。

---

## Config 发现顺序

1. **`PathManager.data_source_handler(data_source_key)/config.py`**
2. 不存在则在 **`handlers/`** 下递归查找包含该 key 的目录中的 **`config.py`**（`PathManager.find_config_recursively`）

---

## Provider 发现

- **`DataSourceProviderHelper.discover_provider_classes()`** 使用 **`ClassDiscovery`** 扫描 **`userspace.data_source.providers`**，将 **`BaseProvider`** 子类注册为可实例化 Provider（细节见 `provider_helper.py`）。

---

## 执行与 `is_dry_run`

- CONFIG 顶层 **`is_dry_run`**（经 `DataSourceConfig.get_is_dry_run()`）为真时：**跳过写库**，仍可走抓取与标准化（见 Handler 管线）。

---

## 相关文档

- [API.md](API.md)
- [DECISIONS.md](DECISIONS.md)
