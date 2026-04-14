# Data Source 模块（`modules.data_source`）

从 **`userspace/data_source/mapping.py`**（`DATA_SOURCES`）与各 handler 的 **`config.py`**（`CONFIG`）驱动：为每个启用的 **data source key** 加载绑定表 **schema**（`DataManager.get_table(table).load_schema()`）、实例化 **Handler** 与全局 **Provider**，由 **`DataSourceExecutionScheduler`** 按依赖 **拓扑排序** 串行执行，将第三方 API 结果规范化后写入数据库（**`is_dry_run`** 时跳过写入）。

## 适用场景

- 从 Tushare / AKShare / 东财等 **Provider** 拉数并落库。
- 多数据源之间存在 **依赖**（如先拉股票列表再拉 K 线），需统一调度顺序。
- 与 **`core/tables`** 表结构对齐，避免维护独立 schema 文件。

## 快速开始

```python
from core.modules.data_source import DataSourceManager

mgr = DataSourceManager(is_verbose=True)
mgr.execute()  # 运行 mapping 中所有 is_enabled 的数据源
```

用户侧目录约定见 [`docs/DESIGN.md`](docs/DESIGN.md)；扩展说明另见 **`userspace/data_source/README.md`**（若存在）。

## 目录结构（本模块）

```text
core/modules/data_source/
├── module_info.yaml
├── README.md
├── data_source_manager.py
├── execution_scheduler.py
├── renew_manager.py
├── base_class/
├── data_class/
├── service/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 模块依赖（`module_info.yaml`）

- **`modules.data_manager`**：表 schema、写库 Model。
- **`infra.project_context`**：`PathManager`（mapping、handlers、providers 路径）。
- **`infra.discovery`**：扫描 **`userspace.data_source.providers`** 注册 Provider 类。

## 测试

```bash
python3 -m pytest core/modules/data_source/__test__/ -q
```

## 相关文档

- [架构与调度](docs/ARCHITECTURE.md)
- [配置与约定](docs/DESIGN.md)
- [公开 API](docs/API.md)
- [设计决策](docs/DECISIONS.md)
