# AI 通道（`infra.ai`）

**模块：** `infra.ai` · **版本：** `0.2.0`

**最低支持核心版本：** `>=0.6.0`

## 简介

本机 AI 供应商通道：发现用户装了哪些供应商、写入 API Key、发 OpenAI 兼容补全。官网会员通道不在本模块（见 `modules.ntq_external`）。多轮对话与工具调度是 Agent 的事。

## 适用场景

- 设置页列出本机供应商并保存 API Key
- Agent / 工具对自备供应商做一次裸补全
- 业务层（如会员通道）经 `complete_http` 注入已解析端点

## 模块依赖

- `infra.discovery`：扫描本机供应商目录
- `infra.project_context`：`llm_providers` 路径

## 设计初衷

- **要解决的问题：** 把「HTTP 调模型」和「官网 / Agent 业务」分开；删除官网客户端后本机供应商仍可用。
- **明确不做：** 会员凭证、多轮对话、工具调度、系统提示词。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [架构](./docs/ARCHITECTURE.md)
- [设计与决策](./docs/DECISIONS.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
