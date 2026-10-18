# Agent — 快速开始

**模块：** `modules.agent` · **版本：** `0.1.0`

查看工具清单，或直接新建一个空策略。

---

## 前置条件

新建策略需要 `userspace/strategies/_template/empty_strategy/`。本版不读取 API Key，也不发网络请求。

---

## 最小示例

```python
from core.modules.agent import Agent

for tool in Agent.list_tools():
    print(tool.name, tool.implemented)

Agent.call_tool("create_strategy", {"key": "macd_cross"})
```

**预期结果：** 打印工具名。`create_strategy` 为 `True`，其余为 `False`。调用后在 `userspace/strategies/macd_cross/` 出现空策略，`meta.key` 为 `macd_cross`。目录已存在时返回 `ok: false`，不覆盖。

---

## 下一步

- [API.md](./API.md)
- [设计](./docs/DESIGN.md)
