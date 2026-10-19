# Agent — 快速开始

**模块：** `modules.agent` · **版本：** `0.1.0`

查看工具清单，或直接新建一个空策略。

---

## 前置条件

新建策略需要 `userspace/strategies/_template/empty_strategy/`。`Agent.run` 使用本机已装载的会员凭证，经会员通道 `ntq` 调用。官网根地址只认 `userspace/system/config/membership.json` 的 `base_url`（缺省为生产官网）；AI / profile 等路径由其派生。开发自测本机密钥时设 `NTQ_AGENT_OWN_KEYS=1`。

---

## 最小示例

```python
from core.modules.agent import Agent

for tool in Agent.list_tools():
    print(tool.name, tool.implemented)

Agent.call_tool("create_strategy", {"key": "macd_cross"})
```

**预期结果：** 已实现的工具打印 `True`。`create_strategy` 在 `userspace/strategies/macd_cross/` 放一个空策略，`meta.key` 为 `macd_cross`。目录已存在时返回 `ok: false`，不覆盖。

---

## 下一步

- [API.md](./API.md)
- [设计](./docs/DESIGN.md)
