# Provider、Navigator 与本地/远端职责

**版本：** `0.1.0`  
**状态：** 产品约定（名词与边界以此为准）

---

## 一句话

| 侧 | 重心 |
|----|------|
| **本地 App** | 组织信息（context）、跑流程、执行本机工具 |
| **远端 Website（仅 ntq）** | 调度用哪个大模型、计量与消耗 |

本地**不**为 `ntq` 挑选 DeepSeek / 智谱等具体模型；App 甚至不必知道 ntq 背后用了几个模型。

---

## 统一名词

| 名词 | 含义 | 不要叫成 |
|------|------|----------|
| **Provider** | 用户选定的一路 AI 出入口。二选一：`ntq`（产品默认）或用户自备供应商之一（只能选 1 个） | 「通道里再拆三个 provider」 |
| **Navigator** | **本地**意图理解与分流：输出有序处理清单（原「门禁 / gate」）。Website 的 `phase=navigate` **只选分流模型**，不代替本机出 kinds | 「分流在远端做完」「与计费档 ask/work 混称」 |
| **处理方式 / 流向** | Navigator 之后的分支，如 identity、advice、out_of_scope、guide、worker 等 | Provider |
| **Context** | App 组给模型的材料：用户话、会话、说明书摘录、工具摘要、准则等 | — |

**Provider 与「选哪路出站」一一对应**：选了 `ntq` 就全程打官网会员通道；选了 `openai` 就全程打该本机供应商。本地准则是 **一个 Provider 干到底**。

---

## 两种 Provider（本地可见的全部）

```text
┌─────────────────────┐     ┌──────────────────────────┐
│ Provider = ntq      │     │ Provider = 用户自备 (×1)  │
│ 唯一出入口 → Website│     │ 唯一出入口 → 该供应商 API │
└─────────────────────┘     └──────────────────────────┘
            │                            │
            └────────────┬───────────────┘
                         ▼
              同一套 Agent 流程
         （组 context → Navigator → 流向 → 工具）
```

| | **ntq** | **用户自备** |
|--|---------|--------------|
| 出站 | 会员凭证 → Website | 用户 API Key → 该供应商 |
| 谁选模型 | **仅 Website** 调度（分流用谁、问答用谁、写代码用谁） | 就是用户选的那一个模型/供应商 |
| App 是否知道背后几个模型 | **否**（不感知、不配置 DS/GLM 清单） | 不涉及多模型调度 |
| 计费 | Website / 猫粮等（远端） | 用户与供应商之间；不计 NTQ 猫粮 |

开发用本机多 key 调试（若仍存在）属于 **用户自备** 变体，**不是** ntq Provider 的内部组成。

---

## 同一套 Agent 流程

无论哪个 Provider：

1. **组 context**（说明书、会话、工具说明、红线准则等）
2. **Navigator**：根据用户话得到处理清单（可多意图排队）
3. **按清单执行流向**（含拒绝、固定文案、guide、worker…）
4. **本机执行工具**（写策略、回测、读报告等），结果再拼回 context

差别只在：**每一步需要模型补全时，请求打到当前选定的那一个 Provider 出入口**。

- 用户自备：Navigator 与各流向的补全 = 同一供应商。  
- ntq：每次补全仍只调 `provider_id=ntq`；Website 在远端决定本次用哪颗模型、如何计费。

---

## 本地 vs 远端

```text
App（重信息与流程）              Website（重调度与消耗）
─────────────────              ─────────────────────
选 Provider                    （仅 ntq）收请求
拼 messages / context          选模型（如分流 DS、问答 GLM…）
Navigator 协议与金标（产品语义）  执行推理、计量猫粮
跑流向状态机                   返回文本 / 结构化结果
执行本机工具、写 userspace
```

**App 负责：** 信息齐不齐、流程对不对、工具安不安全。  
**Website 负责：** 算力落在哪颗模型、花多少钱、内部 fallback。

---

## 明确不做（本地）

- 不为 `ntq` 维护「router=deepseek / ask=zhipu」一类**本地模型挑选表**
- 不在 App 内根据流向把 ntq 请求拆到多个本机供应商
- 不把计费档名字（Website 内部 lane `ask`/`work`）当成 Provider 或流向名词

远端只认 `ntq.phase` / `ntq.intent`；内部 lane 与猫粮钱包是 Website 实现细节，不是第二种 Provider。

---

## 实现入口

- Provider：`core/provider.py`（`resolve_provider`）
- Navigator：`core/navigator/`
- 流程：`Agent.run` → `RunLoop`（全程同一 `provider.id`）
- 出站：`infra.ai.AiChannel.complete`
- 会员 ntq：`ntq_external`（Website）
- **远端状态协议：** [NTQ_REMOTE_PROTOCOL.md](./NTQ_REMOTE_PROTOCOL.md)（`ntq.phase` / `ntq.intent`）
