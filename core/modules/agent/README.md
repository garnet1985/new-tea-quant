# Agent（`modules.agent`）

**模块：** `modules.agent` · **版本：** `0.1.0`

按模型给出的调用单在本机执行 NTQ 工具；选定 Provider 后经 Navigator 进各流向。对外入口为 `Agent`。目录结构分三层：`core/code/` 可执行逻辑、`core/content/` 文案与说明书、`evaluate/` 分流金标评测。

## 适用场景

- 查看工具清单
- `Agent.run`：Provider（`ntq` 或某一个自备）→ Navigator → guider / worker / 工具

## 模块依赖

- `infra.ai`
- `infra.discovery`
- `infra.project_context`
## 设计初衷

- **本地**重信息与流程；**远端（ntq）**重模型调度与消耗。一个 Provider 干到底。
- **明确不做：** 不在 App 内为 ntq 挑 DS/GLM；不发现供应商、不保存 API Key（`infra.ai`）。

## 相关文档

- [Provider 与 Navigator（约定）](./docs/PROVIDER_AND_NAVIGATOR.md)
- [架构](./docs/ARCHITECTURE.md)
- [远端状态协议](./docs/NTQ_REMOTE_PROTOCOL.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
