# Agent（`modules.agent`）

按模型给出的调用单，在本机执行已登记的 NTQ 工具。对外入口为 `Agent`（内部由 `AgentManager` 编排，不导出）。工具说明与异常见 `contracts`。

当前工具已经覆盖新建、写代码、校验、后台运行、读进度、读执行报告、读归因报告和读扫描摘要。`Agent.run` 会把一句话交给会员通道上的 glm-4-flash，执行它返回的调用单，再把摘要送回去。

## 适用场景

- 查看 agent 准备交给模型的工具清单
- 后续：用户用一句话新建策略、写入钩子并启动回测

## 模块依赖

- `infra.project_context`：userspace 根路径，以及策略 / 标签 / 适配器目录
- `modules.assistant`：`Assistant.complete` 把消息发给供应商。agent 不读取密钥，也不自己发 HTTP

## 设计初衷

- **要解决的问题：** 把「模型决定下一步」和「本机执行」分开，并让写入范围由代码强制。
- **明确不做：** 不发现供应商、不保存 API Key、不替代 `Assistant.chat` 的百科问答。官网代理只转发文本，所以调用单写在 JSON 里，而不是 OpenAI 的 tools 字段。

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
