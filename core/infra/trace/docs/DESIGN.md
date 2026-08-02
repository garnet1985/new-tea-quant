# Design — infra.trace

**版本：** `0.2.0`

## 模块内部分层

- `contracts.py`：`TraceEvent` / `TraceConfig` / `TraceConsent` / `FlushBudget`
- `core/services/*Service`：全部用类静态方法，不暴露自由函数
- Facade `Trace`：唯一公开入口，静态调用

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅静态 Facade | 无需实例化 |
| 默认开关 | opt-in，默认关 | 隐私；同意存 `system/config` 而非 `.ntq`（避免 cache cleanup 丢同意） |
| track | 只写本地队列 | 不阻塞业务；网站不可达可补发 |
| 身份 | 匿名 `installation_id` | 不用 IP/电脑名；IP 仅服务端 Flood |
| 体字段 | 白名单 | 禁止路径/token/原始错误文 |
| 积压 | 删最旧 + extreme 预算 | 用户量小，无长连接 |
| 公开稳定性 | 最高 `beta` | core `0.x` |

## 本地文件队列

一事件一 JSON；超 `queue_max` 删最旧。CLI 短进程预算 flush；BFF daemon drain，靠 rename 抢占。

## 预算

| 名称 | 时间 | 条数 |
|------|------|------|
| standard | 1s | 5 |
| extreme | 2s | 10 |

## HTTP

stdlib `urllib`，短超时；客户端无 HMAC。
