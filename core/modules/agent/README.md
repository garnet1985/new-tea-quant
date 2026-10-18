# Agent（`modules.agent`）

按模型给出的调用单，在本机执行已登记的 NTQ 工具。对外入口为 `Agent`（内部由 `AgentManager` 编排，不导出）。工具说明与异常见 `contracts`。

当前是骨架：工具已登记但都未实现，运行循环尚未接通模型。

## 适用场景

- 查看 agent 准备交给模型的工具清单
- 后续：用户用一句话新建策略、写入钩子并启动回测

## 模块依赖

- `infra.project_context`：userspace 根路径，以及策略 / 标签 / 适配器目录

模型通道下一步依赖 `modules.assistant` 的公开入口，不 deep-import 其 HTTP 客户端。

## 设计初衷

- **要解决的问题：** 把「模型决定下一步」和「本机执行」分开，并让写入范围由代码强制。
- **明确不做：** 不发现供应商、不保存 API Key、不替代 `Assistant.chat` 的百科问答。不在本版执行工具或调用大模型。

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.agent import Agent`；类型 `from core.modules.agent.contracts import AgentError, ToolSpec`。

**Q：为什么不写在 assistant 里？**  
A：assistant 负责把一轮文字发给供应商。agent 负责工具清单、写入准则和调用循环。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
