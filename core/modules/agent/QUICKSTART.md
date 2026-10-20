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

## 用户扩展（可选）

目录：`userspace/extensions/agent/`。**除 tool 外只写 Markdown。** New Tea Quant 不对用户扩展的正确性与后果负责；与产品红线冲突时以产品为准。

```text
userspace/extensions/agent/
├── tools/my_tool/tool.py     # 仅新增工具（外接 API 或包装本机 NTQ）
├── templates/backtest_price.md   # 覆盖内置呈现；或新 scenario.md + frontmatter match
└── prompts/
    ├── context.md            # 喜好 / 背景（追加）
    ├── worker.md
    ├── guider.md
    └── present.md
```

`tool.py` 最小形状：

```python
TOOL = {
    "name": "my_tool",
    "description": "……",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}

def run(arguments):
    return {"ok": True, "note": "hello"}
```

新呈现 scenario（自动命中需 frontmatter）：

```markdown
---
match:
  tool: read_execution_report
  layer: portfolio
  user_re: 总结|解读
---

# 我的资金层版式
…
```

---

## 下一步

- [API.md](./API.md)
- [架构](./docs/ARCHITECTURE.md)
- [Provider 与 Navigator](./docs/PROVIDER_AND_NAVIGATOR.md)
