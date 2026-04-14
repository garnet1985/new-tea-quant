# Logging 设计说明

**版本：** `0.2.0`

本文档描述 `infra.logging` 的配置字段语义、初始化顺序及与 CLI 的关系；实现以 `logging_manager.py` 为准。

---

## 配置来源

当 `LoggingManager.setup_logging(config=None)` 时，配置来自：

```text
ConfigManager.load_core_config(
    "logging",
    deep_merge_fields=set(),
    override_fields=set(),
)
```

即合并 `core/default_config/logging.json` 与用户空间 `userspace/config/logging.json`；若加载失败或为空，则按代码内默认值处理。

---

## 配置键

| 键 | 含义 |
| --- | --- |
| `level` | 根 logger 级别名，字符串，如 `INFO`、`DEBUG`；非法名则回退为 `INFO`。 |
| `format` | `logging.Formatter` 的格式串。 |
| `datefmt` | 时间字段格式串。 |
| `module_levels` | 字典：`logger 名称 -> 级别名字符串`，为对应 `logging.getLogger(name)` 单独 `setLevel`（非法级别名则使用该 logger 回退到根级别解析结果）。 |

默认 `format` / `datefmt` 与 `core/default_config/logging.json` 中一致；`module_levels` 可选，用于例如将 `core` 命名空间下 logger 设为特定级别。

---

## 初始化行为

1. 若 `_configured` 已为真，直接返回（幂等）。
2. 解析 `level`、`format`、`datefmt`，取得根 logger。
3. 若根 logger **没有** 任何 handler：调用 `logging.basicConfig(level=..., format=..., datefmt=...)`。
4. 若根 logger **已有** handler：仅 `root_logger.setLevel(level)`（不重复 `basicConfig`）。
5. 遍历 `module_levels`，为每个命名 logger 设置级别。
6. 将 `_configured` 置为真。

---

## 与 `start-cli.py` 的交互

`start-cli.py` 在 `main()` 中于解析参数之后调用 `LoggingManager.setup_logging()`。若用户指定 `--verbose`，在 setup 之后对根 logger 执行 `logging.getLogger().setLevel(logging.DEBUG)`，从而在保持配置文件格式的前提下临时提高详细程度。

---

## 使用约定

业务与基础设施代码推荐使用：

```python
import logging
logger = logging.getLogger(__name__)
```

在进程早期已调用 `LoggingManager.setup_logging()` 的前提下，上述 logger 会继承根 handler；若 `module_levels` 中为该 **完整 logger 名称** 配置了级别，则会对该名称调用 `setLevel`。子 logger 与父 logger 的级别关系遵循标准库 `logging` 的传播与有效级别规则。
