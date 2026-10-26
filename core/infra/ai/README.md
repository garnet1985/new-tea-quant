# AI 通道（`infra.ai`）

**模块：** `infra.ai` · **版本：** `0.1.0`

发现 userspace LLM 供应商、写入 API Key，并发送 OpenAI 兼容的裸补全。对外入口为 `AiChannel`。**不做：** 百科挑文档、业务门禁、工具循环（均在 `modules.agent`）。

## 适用场景

- 设置页写入 / 读取 AI 供应商 Key，或测试 Key 连通性
- agent 模块调用时发送一次裸补全（多轮循环、工具调用由 agent 自己编排）

## 模块依赖

- `infra.discovery`：发现模块：自动发现一些带有特征的文件/类/文件夹的模块，用来服务于用户自定义的功能文件和类。
- `infra.project_context`：项目上下文模块：提供常用路径，配置，缓存，项目上下文信息的模块。
## 设计初衷

- **要解决的问题：** 把"和模型供应商 HTTP 交互"与"业务逻辑（Agent）"分离。供应商可热切换（用户自带 token 注册）。
- **明确不做：** 不做 Agent 的多轮对话、工具调度、系统提示词编排——这些全在 `modules.agent`。

## 相关文档

- [门面 `AiChannel` 实现](./ai_channel.py)
