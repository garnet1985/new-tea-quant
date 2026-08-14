# Design — infra.trace

**版本：** `0.1.0`

## 模块内部分层

- `core/defaults.py`：`TraceDefaults` — 内置 URL / 超时等**唯一源**
- `contracts.py`：`TraceEvent` / `TraceConfig` / `TraceConsent` / `SendBudget`（默认值引用 TraceDefaults）
- `core/services/*Service`：类静态方法
- Facade `Trace`：唯一公开入口

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅静态 Facade | 无需实例化 |
| 默认开关 | opt-in，默认关 | 隐私；同意存 `system/config` 而非 `.ntq` |
| 默认 URL | `TraceDefaults.TARGET_URL` | 单源；易发现 |
| 覆盖 | env > `trace.json` > defaults | 运维可改目标站，无需改代码 |
| track | 立刻 POST；失败入队 | 短进程也能尽量送达 |
| queue | 只写本地队列 | 非阻塞批量 |
| send | 按预算发送队列 | 主动推送 / 退出收尾 |
| 体字段 | 脱敏 | 禁止路径/token |
| 公开稳定性 | 最高 `beta` | core `0.x` |

## 预算

| 名称 | 时间 | 条数 |
|------|------|------|
| standard | 1s | 5 |
| extreme | 2s | 10 |

## HTTP

stdlib `urllib`，短超时；客户端无 HMAC。
