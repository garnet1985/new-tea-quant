# Agent — 架构

**版本：** `0.1.0`

名词与本地/远端边界见 [PROVIDER_AND_NAVIGATOR.md](./PROVIDER_AND_NAVIGATOR.md)。  
状态协议见 [NTQ_REMOTE_PROTOCOL.md](./NTQ_REMOTE_PROTOCOL.md)。

---

## 职责

**App（本地）**

- 选定 Provider（`ntq` 或某一个自备）
- **Navigator：意图分流**（输出 guide / worker / …）——**不是** Website 的事
- 组织 context、流向、本机工具

**Website（仅 Provider=ntq）**

- 按 `ntq.phase` / `ntq.intent` **选上游模型与计费**
- **不**替 App 做意图分类

---

## 目录分层（内容 / 功能分离）

| 目录 | 受众 | 规则 |
|------|------|------|
| `prompts/` | 模型 | **md only**；禁止在 `core/` 堆大段中文 system / nudge / 固定回复 |
| `core/` | 运行时 | 只 `load_prompt` / `load_nudge` / `load_reply`；禁止大段中文常量 |
| `context/` | 白名单说明书 | allowlist 注入 guide；**默认不进** worker 系统提示全文 |
| `eval/` | 离线评测 | 不被 `run_loop` import |
| `docs/` | 开发者 | 不注入模型 |

```text
core/modules/agent/
├── prompts/                 # 给模型：md only
│   ├── common/{identity,session_preamble}.md
│   ├── navigate/classifier.md
│   ├── guide/{arch,arch_user,wiki}.md
│   ├── worker/system.md     # {{identity}} {{tools}}
│   ├── nudges/{worker,guide}.md
│   └── replies.md
├── core/                    # 功能（暂不改名 runtime）
│   ├── prompt_store.py      # loader
│   ├── provider.py / run_loop.py / loop_runtime.py
│   ├── navigator/           # 本地意图（正则在 patterns，文案在 prompts）
│   ├── roles/guide|worker
│   └── tools/strategy/
├── context/                 # 白名单说明书 + allowlist
├── eval/                    # gold_set / harness
└── docs/
```

---

## 数据流

```text
用户话 + providerId
  → resolve_provider
  → navigator.route           # 本地分流（文案：prompts/navigate）
  → guide / worker            # 文案：prompts/guide|worker
  → complete(同一 provider_id；ntq 时带 ntq.phase / ntq.intent)
```

---

## 依赖

- `infra.project_context`
- `infra.ai`
- `ntq_external`（仅 Provider=`ntq`）
