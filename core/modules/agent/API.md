# Agent API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.6.0`

> 须与 `module_info.yaml` 一致。公开入口状态最高 **`experimental`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Agent`。`ToolSpec` 与 `AgentError` 从 [`contracts.py`](./contracts.py) 导入。实现位于 `core/code/`，禁止 deep-import。

---

## Agent

**描述：** AI agent 门面（静态 API）。列出工具，执行调用单；`run` 走 Provider → Navigator → guider/worker。

### list_tools

`Agent.list_tools() -> list[ToolSpec]`

- **类型：** `static`
- **状态：** `experimental`
- **引入版本：** `0.1.0`
- **描述：** 返回已登记的工具说明。`implemented` 为假时，运行循环不得执行该工具
- **参数：** 无
- **返回值：** `list[ToolSpec]`
- **举例：**

```python
from core.modules.agent import Agent

names = [tool.name for tool in Agent.list_tools()]
```

### call_tool

`Agent.call_tool(name: str, arguments: dict | None = None) -> dict`

- **类型：** `static`
- **状态：** `experimental`
- **引入版本：** `0.1.0`
- **描述：** 执行一张调用单。未知工具或尚未实现时抛 `AgentError`。工具自己的失败（例如目录已存在）放在返回值的 `ok: false` 里
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 工具名，须在 `list_tools` 中 |
| `arguments` (可选) | `dict \| None` | 该工具的参数；缺省为 `{}` |

- **返回值：** `dict` — 给模型的摘要，不含绝对路径
- **错误与异常：** `AgentError` — 未知工具、工具尚未实现、参数不是对象
- **举例：**

```python
from core.modules.agent import Agent

Agent.call_tool("create_strategy", {"key": "macd_cross"})
```

### run

`Agent.run(content: str, *, session_id: Optional[str] = None, provider_id: Optional[str] = None) -> dict`

- **类型：** `static`
- **状态：** `experimental`
- **引入版本：** `0.1.0`
- **描述：** 锁定 Provider（`ntq` 或某一个自备）后，Navigator 分流再进 guider/worker；全程同一 `provider_id` 出站。`ntq` 打 Website（模型调度与猫粮在远端）；自备 key 不计 NTQ 用量。一轮模型调用上限见 `conf.PIPELINE_MAX_STEPS`。开发可设 `NTQ_AGENT_OWN_KEYS=1`；Navigator 对照臂可设 `NTQ_AGENT_NAVIGATOR_MODE=regex`
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `content` | `str` | 用户需求；空白则失败 |
| `session_id` (可选) | `str \| None` | 会话名，默认 `default` |
| `provider_id` (可选) | `str \| None` | 缺省走 ntq（或 OWN_KEYS 开发默认） |

- **返回值：** `dict` — `reply`、`handoff`（是否进过执行者）、`mode`（`ask`\|`work`，与 `handoff` 同义的 UI 简写，**不是** `ntq.phase`）、`catfood_spent`、`balance`
- **错误与异常：** `AgentError` — 消息为空、模型通道失败、调用次数用尽、工具名未知
- **举例：**

```python
from core.modules.agent import Agent

print(Agent.run("读一下 demo/regression/rsi/rsi_v1_baseline 的枚举报告，不要回测")["reply"])
```

### clear_session

`Agent.clear_session(session_id: Optional[str] = None) -> None`

- **类型：** `static`
- **状态：** `experimental`
- **引入版本：** `0.1.0`
- **描述：** 清空会话对话与局部任务状态。不清除跨会话偏好，也不删除策略或报告

### remember / forget / list_preferences

`Agent.remember(rule: str) -> list[str]`  
`Agent.forget(rule: str) -> list[str]`  
`Agent.list_preferences() -> list[str]`

- **类型：** `static`
- **状态：** `experimental`
- **引入版本：** `0.1.0`
- **描述：** 读写跨会话偏好（`userspace/.ntq/agent/preferences.json`）

---

## ToolSpec

**描述：** 交给模型的工具说明（`contracts.ToolSpec`）。不含可执行体。

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 工具名，调用单只能使用清单内的名字 |
| `description` | `str` | 给模型看的用途说明 |
| `parameters` | `dict` | JSON Schema 对象 |
| `implemented` | `bool` | 本机是否已有执行函数 |

---

## AgentError

**描述：** 路径不在允许范围，或运行循环尚不能继续（`contracts.AgentError`）。异常消息不含 api_key。
