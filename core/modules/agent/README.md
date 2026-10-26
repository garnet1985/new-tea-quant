# Agent（`modules.agent`）

**模块：** `modules.agent` · **版本：** `0.1.0`

## 简介

NTQ 的 AI 助手。你跟它说想干嘛，它在后台调用框架自带的工具帮你完成——写策略、读报告、跑扫描。

## 适用场景

- 想写一个新策略但不想从零手写代码，跟 Agent 说需求，它生成策略文件并帮你跑起来
- 回测跑完了，不想自己翻数据，让 Agent 读报告总结盈亏和持仓变化
- 想看看某个策略在全市场能抓到哪些机会，让 Agent 帮你跑扫描

## 模块依赖

- `infra.ai`：提供 AI 模型的连接和调用
- `infra.discovery`：自动发现有哪些工具和供应商可用
- `infra.project_context`：定位用户数据目录

## 设计初衷

- **要解决的问题：** 把 AI 和 NTQ 工具接起来，让用户用自然语言就能操作框架。
- **明确不做：** 不负责发现 AI 供应商、不保存模型密钥（那是 `infra.ai` 的事）；也不挑用哪个模型——模型选择在 ntq 官网侧或用户自备。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
- [术语表](./glossary.yaml)
- [快速开始](./QUICKSTART.md)
