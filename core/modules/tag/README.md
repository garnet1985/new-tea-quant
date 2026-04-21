# Tag 模块（`modules.tag`）

**`TagManager`** 在 **`userspace/tags/`**（或 `PathManager.tags()` 指向的目录）下发现场景：每个子目录含 **`settings.py`** 与 **`tag_worker.py`**（继承 **`BaseTagWorker`**）。执行时按 **`TagUpdateMode`**（增量 / 全量刷新）构建 Job，经 **`ProcessWorker`** 在子进程中逐实体、逐交易日调用 **`calculate_tag`**，结果经 **`DataManager.stock.tags`** 批量写入。

仓库内专题说明见 **[用户指南：标签系统](../../../userspace/tags/USER_GUIDE.md)**；示例配置见 **`userspace/tags/`**。

## 适用场景

- 把「某段逻辑在固定数据契约下的切片结果」沉淀为可复用、可追溯的 JSON 标签，供策略与分析多次读取。
- 需要按交易日 **`as_of`** 单调推进、依赖 **DataCursor** 前缀视图避免未来数据泄露的批量打标。

## 快速开始

```python
from core.modules.tag import TagManager

mgr = TagManager()
mgr.execute()  # 跑 scenarios 根下全部场景
# mgr.execute("my_scenario")
# mgr.execute(settings={...})  # 临时 settings，不落盘发现缓存
```

自定义 Worker：在场景目录中实现 **`tag_worker.py`**，类继承 **`BaseTagWorker`** 并实现 **`calculate_tag`**（见 [API](docs/API.md)）。

## 目录结构

```text
core/modules/tag/
├── module_info.yaml
├── README.md
├── __init__.py
├── tag_manager.py
├── base_tag_worker.py
├── config.py
├── enums.py
├── components/
└── models/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 模块依赖（`module_info.yaml`）

运行时依赖 **`modules.data_manager`**、**`modules.data_contract`**、**`modules.data_cursor`**、**`infra.project_context`**、**`infra.worker`**。

## 相关文档

- [架构与边界](docs/ARCHITECTURE.md)
- [子模块与数据流](docs/DESIGN.md)
- [公开 API](docs/API.md)
- [设计决策](docs/DECISIONS.md)
