# Agent（`modules.agent`）

按模型给出的调用单在本机执行 NTQ 工具；选定 Provider 后经 Navigator 进各流向。对外入口为 `Agent`。

## 适用场景

- 查看工具清单
- `Agent.run`：Provider（`ntq` 或某一个自备）→ 组 context → Navigator → 流向 / 工具

## 模块依赖

- `infra.project_context`
- `infra.ai`：`AiChannel.complete`（不读密钥文件、不自管 HTTP）

## 设计初衷

- **本地**重信息与流程；**远端（ntq）**重模型调度与消耗。一个 Provider 干到底。
- **明确不做：** 不在 App 内为 ntq 挑 DS/GLM；不发现供应商、不保存 API Key（`infra.ai`）。

## 相关文档

- [Provider 与 Navigator（约定）](./docs/PROVIDER_AND_NAVIGATOR.md)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [公开 API](./API.md)
