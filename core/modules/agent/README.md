# Agent（`modules.agent`）

按模型给出的调用单，在本机执行已登记的 NTQ 工具；并在门禁后方做说明书轻问答。对外入口为 `Agent`。

## 适用场景

- 查看工具清单
- `Agent.run`：会员 NTQ AI（可工具）或本机 `provider_id`（BYOK 百科）

## 模块依赖

- `infra.project_context`
- `infra.ai`：`AiChannel.complete`（不读密钥文件、不自管 HTTP）

## 设计初衷

- **要解决的问题：** 把「模型决定下一步」和「本机执行」分开，写入范围由代码强制；知识拼装属业务。
- **明确不做：** 不发现供应商、不保存 API Key（`infra.ai`）。

## 相关文档

- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [公开 API](./API.md)
