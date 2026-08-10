# Data Source 设计说明

**模块：** `modules.data_source` · **版本：** `0.2.0`

API 以根目录 [API.md](../API.md) 为准。实现以 `core/data_source_manager.py`、`core/service/manager_helper.py` 为准。

---

## 1. userspace 布局

| 路径 | 作用 |
| --- | --- |
| `userspace/data_source/mapping.py` | **`DATA_SOURCES`** |
| `userspace/data_source/handlers/<name>/config.py` | 各源 **`CONFIG`**（顶层 **`table`**） |
| `userspace/data_source/handlers/.../handler.py` | Handler 实现 |
| `userspace/data_source/providers/` | Provider 包 |

---

## 2. Schema 与表绑定

- **`CONFIG.table`** → **`DataManager.get_table`** → **`load_schema()`**
- Handler 输出与 schema 对齐；不维护独立 schema 文件

---

## 3. Config / Provider 发现

1. handler config：约定路径或 `handlers/` 树内按 key 查找
2. Provider：扫描 `userspace.data_source.providers` 下 `BaseProvider` 子类

---

## 4. 执行与 `is_dry_run`

- **`is_dry_run`** 为真时跳过写库，仍可抓取与标准化

---

## 5. 设计决策

### 决策 1：Schema 以数据库表为准

**决策：** `CONFIG.table` 绑定已注册表；`load_schema()` 为唯一字段契约。

### 决策 2：单一入口 `DataSourceManager.execute` / `renew`

**决策：** discover → 建 handler → scheduler 拓扑执行。

### 决策 3：数据源之间串行 + 拓扑序

**决策：** `DataSourceExecutionScheduler` 拓扑排序；reserved dependency 由 `reserved_dependencies` 解析。

### 决策 4：Provider 全量发现、Handler 按名取用

**决策：** 初始化发现全部 Provider；handler 按 `provider_name` 取用。

### 决策 5：TQDM 在 import 时禁用

**决策：** `base_handler` 加载时设 `TQDM_DISABLE=1`。

### 决策 6：日期范围无独立 RenewManager

**决策：** 由 `DateRangeService` / `date_range_helper` / `RenewCommonHelper` 统一计算；已删除未接入的 RenewManager 与三模式 RenewService 占位实现。

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
