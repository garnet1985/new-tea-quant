# Agent — 快速开始

**模块：** `modules.agent` · **版本：** `0.1.0`

查看工具清单，或直接新建一个空策略。

---

## 前置条件

新建策略需要 `userspace/strategies/_template/empty_strategy/`。`Agent.run` 默认 Provider=`ntq`（会员凭证 → Website）。官网根地址只认 `userspace/system/config/membership.json` 的 `base_url`。开发自测可设 `NTQ_AGENT_OWN_KEYS=1`（默认本机 deepseek，仍是 own）。

文案在 `core/content/`；超时与步数在 `core/code/conf/conf.py`。

---

## 最小示例

```python
from core.modules.agent import Agent

for tool in Agent.list_tools():
    print(tool.name, tool.implemented)

Agent.call_tool("create_strategy", {"key": "macd_cross"})
```

**预期结果：** 已实现的工具打印 `True`。`create_strategy` 在 `userspace/strategies/macd_cross/` 放一个空策略，`meta.key` 为 `macd_cross`。目录已存在时返回 `ok: false`，不覆盖。

```python
outcome = Agent.run("NTQ 是什么")
print(outcome["reply"], outcome["handoff"], outcome.get("catfood_spent"))
```

---

## 下一步

- [API.md](./API.md)
- [架构](./docs/ARCHITECTURE.md)
- [Provider 与 Navigator](./docs/PROVIDER_AND_NAVIGATOR.md)
