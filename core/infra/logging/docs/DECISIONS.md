# Logging 设计决策

**版本：** `0.2.0`

本文档记录 `infra.logging` 的关键取舍；仅描述当前事实与既定方向，不记录变更历史。

---

## D1 — 单一入口 + 标准库

**决策**：全局日志初始化集中在 `LoggingManager.setup_logging`，底层仅使用标准库 `logging`。

**理由**：降低依赖与认知成本；与现有 `start-cli.py` 及各处 `getLogger(__name__)` 兼容。文件落地、JSON 日志、指标等可作为后续增量，通过同一入口扩展 handler，而非在业务中分散配置。

---

## D2 — 配置走 ConfigManager

**决策**：默认从 `ConfigManager.load_core_config("logging", ...)` 读取配置，与 `core/default_config/logging.json` 及 `userspace/config/logging.json` 对齐。

**理由**：与项目其余模块的配置合并、用户覆盖策略一致，避免单独维护一套 logging 配置文件路径。

---

## D3 — 幂等初始化

**决策**：使用类属性 `_configured`，`setup_logging` 仅在首次调用时生效。

**理由**：防止多次 `basicConfig` 或测试/入口重复调用导致行为不确定；与「进程级一次性配置」模型一致。

---

## D4 — 根已有 handler 时只调级别

**决策**：若根 logger 已存在 handler，则跳过 `basicConfig`，仅 `setLevel`。

**理由**：在嵌入已有日志体系或测试注入 handler 的场景下，避免重复添加默认 handler；级别仍可由配置更新。

---

## D5 — 不强制经本模块获取 Logger

**决策**：业务代码可直接 `logging.getLogger(__name__)`；`LoggingManager.get_logger` 为可选便利方法。

**理由**：符合 Python 社区惯例；初始化一次后所有 logger 共享同一配置树。

---

## 后续可能演进（非承诺）

- 在保持单一入口的前提下增加可选文件 handler、轮转策略（与 `PathManager` 日志目录对齐）。
- 与运行环境（CLI / worker 子进程）协调日志隔离或上下文字段。
