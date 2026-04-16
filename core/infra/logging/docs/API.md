# Logging API 文档

**版本：** `0.2.0`

本模块对外以 `LoggingManager` 为主；业务代码可直接使用标准库 `logging.getLogger(__name__)`。

---

## `LoggingManager`

日志初始化的唯一入口类；状态为类级别（`_configured`），全进程共享。

---

### `setup_logging`

| 项目 | 说明 |
| --- | --- |
| **状态** | 稳定 |
| **描述** | 根据传入配置或 `ConfigManager` 加载结果初始化全局 `logging`：根级别、格式、日期格式，以及可选的 `module_levels`。首次调用后再次调用无效（幂等）。 |
| **诞生版本** | `v0.2.0`（本模块以当前仓库形态为基线） |

**参数**

| 名称 | 类型 | 必须 | 说明 |
| --- | --- | --- | --- |
| `config` | `Optional[Dict[str, Any]]` | 否 `(可选)` | 日志配置字典；为 `None` 时使用 `ConfigManager.load_core_config("logging", ...)` 的合并结果，缺省键由实现内建默认值补齐。 |

**返回值**

| 类型 | 说明 |
| --- | --- |
| `None` | 无 |

---

### `get_logger`

| 项目 | 说明 |
| --- | --- |
| **状态** | 稳定 |
| **描述** | 等价于 `logging.getLogger(name)`，便于统一从本模块获取 logger。 |
| **诞生版本** | `v0.2.0` |

**参数**

| 名称 | 类型 | 必须 | 说明 |
| --- | --- | --- | --- |
| `name` | `Optional[str]` | 否 `(可选)` | Logger 名称；`None` 时对应根 logger。 |

**返回值**

| 类型 | 说明 |
| --- | --- |
| `logging.Logger` | 标准库 Logger 实例。 |

---

## 示例

```python
from core.infra.logging import LoggingManager
import logging

LoggingManager.setup_logging()
logger = logging.getLogger(__name__)
# 或
logger = LoggingManager.get_logger(__name__)
```

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
