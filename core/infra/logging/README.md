# Logging 模块（`infra.logging`）

集中初始化 Python 标准库 `logging`：从 `ConfigManager` 加载合并后的 `logging.json`（`core/default_config/` + `userspace/config/`），设置根 logger 的级别与格式，并可按 logger 名覆盖级别。本模块**不**实现文件轮转、结构化 JSON、远程采集等能力；后续若扩展，应以本入口为单一配置落点，避免各处重复 `basicConfig`。

## 适用场景

- 进程启动时调用一次 `LoggingManager.setup_logging()`，使全局 `logging.getLogger(__name__)` 行为一致。
- 通过 `userspace/config/logging.json` 调整默认级别与格式，无需改代码。

## 快速定位

```text
core/infra/logging/
├── module_info.yaml
├── __init__.py
├── logging_manager.py
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 快速开始

```python
from core.infra.logging import LoggingManager
import logging

LoggingManager.setup_logging()
log = logging.getLogger(__name__)
log.info("ready")
```

CLI 入口 `start-cli.py` 在解析参数后首先调用 `LoggingManager.setup_logging()`；若传入 `--verbose`，会将根 logger 级别提升为 `DEBUG`（见该文件中的处理）。

配置键与合并规则见 [`docs/default_config/user_guide.md`](../../../docs/default_config/user_guide.md) 及本模块 [`docs/DESIGN.md`](docs/DESIGN.md)。

## 文档索引

- [架构与边界](docs/ARCHITECTURE.md)
- [设计与配置流](docs/DESIGN.md)
- [公开 API](docs/API.md)
- [设计决策](docs/DECISIONS.md)
