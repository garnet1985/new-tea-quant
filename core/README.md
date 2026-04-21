# `core/`（框架核心）

业务逻辑、数据库、策略引擎、数据源运行时等均在此目录。**日常扩展策略/数据源请改 `userspace/`，不要 fork 整个 `core/`**，以便跟随上游升级。

- 模块说明：各子包内常有 `README.md`（如 `modules/strategy/README.md`）。  
- 总览文档：[docs/project_overview.md](../docs/project_overview.md)。  

版本号：`python -c "import core; print(core.__version__)"`（与 [CHANGELOG.md](../CHANGELOG.md) 对齐）。
