# Agent — 架构

**版本：** `0.1.0`

`modules.agent` 执行模型点名的 NTQ 工具。供应商、密钥和 HTTP 留在 `modules.assistant`。本版只建立清单和写入准则，不调用模型。

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
│   ├── policy.py            # 写入准则
│   └── run_loop.py          # 循环（尚未接通模型，不导出）
├── API.md / QUICKSTART.md / glossary.yaml
├── __test__/
└── docs/
```

---

## 架构图

```text
Caller
  → Agent.list_tools
       → AgentManager
            → ToolCatalog
            → Policy          # 写文件的工具实现时调用
            → RunLoop         # 下一步才经 Assistant 公开入口请求模型
```

---

## 数据流（待接通）

```text
用户一句话
  → RunLoop 附带 ToolSpec 列表请求模型
  → 调用单 {name, arguments}
  → Policy 校验路径
  → 已实现的工具执行
  → 摘要写回本机运行记录，再次请求模型
  → 人话回复
```

---

## 依赖（结论）

- `infra.project_context`：userspace 与策略 / 标签 / 适配器路径

---

## 相关文档

- [README](../README.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [设计](./DESIGN.md)
- [快速开始](../QUICKSTART.md)
