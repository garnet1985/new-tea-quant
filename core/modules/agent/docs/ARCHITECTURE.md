# Agent — 架构

**版本：** `0.1.0`

名词与本地/远端边界见 [PROVIDER_AND_NAVIGATOR.md](./PROVIDER_AND_NAVIGATOR.md)。

---

## 职责

**App**

- 选定 Provider（`ntq` 或某一个自备）
- 组织 context、Navigator、流向、本机工具

**不负责**

- 为 ntq 挑选背后大模型（Website）
- 供应商发现 / API Key 文件 / 裸 HTTP（`infra.ai`）

---

## 结构

```text
core/modules/agent/
├── agent.py
├── core/
│   ├── provider.py          # 锁定 Provider
│   ├── navigator/           # Navigator（意图清单）
│   ├── knowledge/
│   ├── roles/guide|worker
│   ├── run_loop.py
│   └── tools/strategy/
└── docs/
    └── PROVIDER_AND_NAVIGATOR.md
```

---

## 数据流

```text
用户话 + providerId
  → resolve_provider          # ntq | 某一个 own（一个 id 干到底）
  → 组 context
  → navigator.route(provider_id=…)
  → 流向 + 本机工具
  → complete 一律打同一 provider_id
       ntq → Website 调度模型与计费
       own → 用户供应商
```

---

## 依赖

- `infra.project_context`
- `infra.ai`
- `ntq_external`（仅 Provider=`ntq`）
