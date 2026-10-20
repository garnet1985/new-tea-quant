# Agent — 架构

**版本：** `0.1.0`

名词与本地/远端边界见 [PROVIDER_AND_NAVIGATOR.md](./PROVIDER_AND_NAVIGATOR.md)。  
状态协议见 [NTQ_REMOTE_PROTOCOL.md](./NTQ_REMOTE_PROTOCOL.md)。

---

## 职责

**App（本地）**

- 选定 Provider（`ntq` 或某一个自备）
- **Navigator：意图分流**（输出 guide / worker / …）——**不是** Website 的事
- 组织 content、流向、本机工具

**Website（仅 Provider=ntq）**

- 按 `ntq.phase` / `ntq.intent` **选上游模型与计费**
- **不**替 App 做意图分类

---

## 目录分层

| 目录 | 受众 | 规则 |
|------|------|------|
| `core/code/` | 程序员 | 全部可执行逻辑；禁止堆大段中文文案 |
| `core/content/` | 非程序员 / 模型 | 仅 md、txt、allowlist；由 code 读取 |
| `evaluate/` | 离线分流评测 | 金标 + harness；**不被** pipeline import |
| `docs/` | 开发者 | 不注入模型 |

```text
core/modules/agent/
├── agent.py / contracts.py
├── evaluate/                   # gold_set + harness（evaluate）
├── docs/
└── core/
    ├── code/
    │   ├── pipeline.py / agent_manager.py
    │   ├── navigator/ provider/ session/ tools/ conf/
    │   └── executor/{shared,guider,worker}/
    └── content/
        ├── global/             # whoiam · responsibility · redlines
        ├── specific/
        │   ├── navigator/      # classifier + advice replies
        │   ├── guider/
        │   └── worker/
        └── ntq_wiki/
```

---

## 数据流

```text
用户话 + providerId
  → resolve_provider
  → navigator.route
  → guider / worker（读 content/ → ask → decision → use_tool）
  → complete(同一 provider_id；ntq 时带 ntq.phase / ntq.intent)
```

`Agent.run` 返回里的 `handoff` / `mode`：`mode` 仅为 UI 兼容简写（`work`⇔进过执行者），**不是**远端 `ntq.phase`。

---

## 依赖

- `infra.project_context`
- `infra.ai`
- `ntq_external`（仅 Provider=`ntq`）
