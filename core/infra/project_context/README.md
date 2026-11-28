# Project Context（`infra.project_context`）

**模块：** `infra.project_context` · **版本：** `0.2.2`

**最低支持核心版本：** `>=0.5.0`

## 简介

项目里所有路径和配置的统一入口。找 userspace 在哪、找策略目录在哪、合并默认配置和用户覆盖、读缓存目录——都从这里走，不用每个模块自己拼路径。

## 适用场景

- 想拿 userspace 路径、策略目录、Tag 目录等语义路径
- 想读某个模块的配置，合并 core 默认值和 userspace 覆盖

## 模块依赖

无硬依赖

## 设计初衷

- **要解决的问题：** 路径拼接和配置合并是"任何模块都可能要"的原语，不能散落在各处。
- **明确不做：** 不做业务调度；不往 userspace 写配置。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [快速开始](./QUICKSTART.md)
- [决策](./docs/DECISIONS.md)
