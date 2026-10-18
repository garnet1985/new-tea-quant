# Agent — 架构

**版本：** `0.1.0`

`modules.agent` 执行模型点名的 NTQ 工具。供应商、密钥和 HTTP 留在 `modules.assistant`。`Agent.run` 经 `Assistant.complete` 使用会员通道上的 glm-4-flash。

---

## 职责与边界（结论）

**负责**

- 登记工具名、说明和参数
- 拒绝落在策略、标签、适配器目录之外的写入路径
- 日后编排运行循环：调用单进来，摘要送回

**不负责**

- 发现供应商、读写 API Key、会员通道（`modules.assistant`）
- 百科一轮问答（`Assistant.chat`）
- 策略模拟本身的调度（`modules.strategy`；agent 只在工具实现后调用其门面）
- 浏览器 / Flask

---

## 模块结构图

```text
core/modules/agent/
├── agent.py                 # Facade Agent（唯一对外入口）
├── contracts.py             # ToolSpec / AgentError
├── core/
│   ├── agent_manager.py     # 编排层（不导出）
│   ├── tool_catalog.py      # 工具清单
│   ├── tool_runner.py       # 按名字执行已实现的工具
│   ├── policy.py            # 写入准则
│   ├── session_store.py     # 会话记录、局部状态、跨会话偏好
│   ├── run_loop.py          # 门 + 做事循环（不导出；经 Assistant.complete）
│   └── tools/
│       ├── task_record.py          # 各领域共用的任务记录
│       └── strategy/               # 策略工具；data、tag 以后各自一目录
│           ├── _strategy_key.py
│           ├── background_run.py
│           ├── create_strategy.py
│           ├── read_reports.py
│           ├── validate_strategy.py
│           └── write_strategy_files.py
├── API.md / QUICKSTART.md / glossary.yaml
├── __test__/
└── docs/
```

---

## 架构图

```text
Caller
  → Agent.list_tools / call_tool / run / clear_session / remember
       → AgentManager
            → ToolCatalog
            → Policy          # 写文件的工具实现时调用
            → SessionStore    # preferences / transcript / state
            → RunLoop
                 → Assistant.complete   # 产品：ntq；开发自有密钥：zhipu 门 + deepseek
```

---

## 数据流

```text
用户一句话
  → 拼偏好 + 局部状态 + 最近几轮
  → 免费模型判断 reply 或 handoff
  → 做事时 deepseek-flash + 工具清单
  → JSON 调用单 {tool, arguments}，或 {reply}
  → 已实现的工具执行，刷新 state
  → 摘要作为下一条用户消息送回
  → 人话回复写入 transcript
```

---

## 依赖（结论）

- `infra.project_context`：userspace 与策略 / 标签 / 适配器路径
- `modules.assistant`：`Assistant.complete`

---

## 相关文档

- [README](../README.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [设计](./DESIGN.md)
- [快速开始](../QUICKSTART.md)
