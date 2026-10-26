# Design — infra.trace

**版本：** `0.1.2`

## 模块内部分层

- `core/defaults.py`：`TraceDefaults` — 超时、队列等引擎默认。官网地址在 `modules.ntq_external`
- `contracts.py`：`TraceEvent` / `TraceConfig` / `TraceConsent` / `SendBudget`（默认值引用 TraceDefaults）
- `core/services/*Service`：类静态方法
- Facade `Trace`：唯一公开入口

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 预算

| 名称 | 时间 | 条数 |
|------|------|------|
| standard | 1s | 5 |
| extreme | 2s | 10 |

## HTTP

stdlib `urllib`，短超时；客户端无 HMAC。
