# Design — infra.trace

## 模块内部分层

- `contracts.py`：`TraceEvent` / `TraceConfig` / `FlushBudget`
- `core/services/*Service`：全部用类静态方法，不暴露自由函数
- Facade `Trace`：唯一公开入口，静态调用

## 本地文件队列

一事件一 JSON 文件，避免单文件锁与崩溃损坏整队列。队列超 `queue_max` 时删除最旧文件。

## 双运行态

- **CLI 冷启动**：进程短，入口带预算 flush 即可。
- **BFF 长进程**：daemon 线程定时 drain；与 CLI 共享同一 queue，靠 `queue → inflight/{name}.{pid}` 原子 rename 抢占。

## 预算

| 名称 | 时间 | 条数 |
|------|------|------|
| standard | 1s | 5 |
| extreme | 2s | 10 |

队列深度 ≥ `extreme_depth`（默认 20）时自动用 extreme。不做长连接。

## HTTP

stdlib `urllib`，User-Agent `NTQ-trace/1`，短超时；客户端无 HMAC（防滥用在服务端 Flood）。
