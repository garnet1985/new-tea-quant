# Export / Import（`infra.export_import`）

**模块：** `infra.export_import` · **版本：** `0.2.0`

## 简介

打包和安装。把策略包 / 扩展包打成 zip 导出去，或者从 zip 装进来。安装前可以选择冲突时拒绝、跳过已有、还是覆盖。

## 适用场景

- A 机器写好了一个策略，想打 zip 给 B 机器装上
- 从别人那拿到一个 zip，装到自己的 userspace

## 模块依赖

无硬依赖

## 设计初衷

- **要解决的问题：** 打包、冲突检查、落盘这一套逻辑不该让 Strategy 和 DataSource 各写一遍。
- **明确不做：** 不解析业务依赖图（装完之后发现什么、校验什么，由各业务模块自己做）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [快速开始](./QUICKSTART.md)
- [决策](./docs/DECISIONS.md)
