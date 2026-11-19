# infra.trace — 设计与决策

**模块：** `infra.trace` · **版本：** `0.1.2`

**最低支持核心版本：** `>=0.5.0`

本文记录 infra.trace 模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

为产品提供遥测 / trace 上报能力，同时满足：隐私优先（opt-in，默认关，事件体字段脱敏，禁止路径/token）；短进程（CLI 场景）也能尽量送达；运维可改目标站而无需改代码；core `0.x` 阶段公开面稳定性不超过 `beta`。

## 方案与思路

- **分层与入口：** `core/defaults.py` 提供 `TraceDefaults`（超时、队列等引擎默认，官网地址在 `modules.ntq_external` 登记）；`contracts.py` 定义 `TraceEvent` / `TraceConfig` / `TraceConsent` / `SendBudget`（默认值引用 `TraceDefaults`）；`core/services/*Service` 用类静态方法；对外唯一公开入口是静态 Facade `Trace`。
- **预算档位：**

  | 名称 | 时间 | 条数 |
  |------|------|------|
  | standard | 1s | 5 |
  | extreme | 2s | 10 |

- **HTTP：** 用 stdlib `urllib`，短超时；客户端无 HMAC。
- **发送策略：** `track` 立刻 POST、失败入本地队列（非阻塞批量）；`send` 按预算发送队列（主动推送 / 退出收尾）；覆盖优先级 env > `trace.json` > defaults。

具体拍板见下文 DEC-01。

---

## DEC-01：决策摘要

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅静态 Facade | 无需实例化 |
| 默认开关 | opt-in，默认关 | 隐私；同意存 `system/config` 而非 `.ntq` |
| 默认 URL | `ntq_external` 登记 | trace 不内置官网地址；模块不在则不发送 |
| 覆盖 | env > `trace.json` > defaults | 运维可改目标站，无需改代码 |
| track | 立刻 POST；失败入队 | 短进程也能尽量送达 |
| queue | 只写本地队列 | 非阻塞批量 |
| send | 按预算发送队列 | 主动推送 / 退出收尾 |
| 体字段 | 脱敏 | 禁止路径/token |
| 公开稳定性 | 最高 `beta` | core `0.x` |

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
