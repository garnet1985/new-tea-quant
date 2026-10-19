# Agent — 架构

**版本：** `0.1.0`

`modules.agent` 执行门禁、角色循环与 NTQ 工具。供应商、密钥和 HTTP 在 `infra.ai`。`Agent.run` 经 `AiChannel.complete` 出站。

---

## 职责与边界（结论）

**负责**

- 登记工具、写入准则、会话
- 门禁与 guide / worker
- 知识语料（`context/`）与拼装

**不负责**

- 发现供应商、读写 API Key、裸 HTTP（`infra.ai`）
- 会员 token / 外站配额客户端（`ntq_external`；BFF/agent 可读 quota）

---

## 模块结构图

```text
core/modules/agent/
├── agent.py
├── contracts.py
├── context/                 # 说明书语料
├── core/
│   ├── gate/
│   ├── knowledge/           # 挑文档 / 拼 messages
│   ├── roles/guide|worker
│   ├── loop_runtime.py
│   ├── run_loop.py
│   └── tools/strategy/
└── docs/
```

---

## 数据流

```text
用户一句话 + 可选 providerId
  → gate.router
  → ntq：guide_arch | guide wiki | worker
  → BYOK：百科拼装（knowledge）或拒绝 worker
  → AiChannel.complete
  → 工具执行（仅会员路径）→ transcript
```

---

## 依赖

- `infra.project_context`
- `infra.ai`：`AiChannel.complete`
