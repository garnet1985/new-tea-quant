# Updater（`infra.updater`）

**模块：** `infra.updater` · **版本：** `0.1.0`

## 简介

NTQ 的升级流程编排。在已装环境上原地升级——替换源码、跑数据库迁移脚本、收尾 post-upgrade。升级编排会被拷贝到 userspace，运行时直接调，不 import core 里的版本避免漂移。

## 适用场景

- CLI `python cli.py u` 或 BFF 触发升级时，按编排依次执行
- 新版本数据库 schema 变了，跑迁移脚本

## 模块依赖

- `infra.utils`：通用工具（文件操作等）

## 设计初衷

- **要解决的问题：** 安装和升级是两件事——安装从零装、升级在已有环境上原地改，不能共用一套编排。
- **明确不做：** 不检查远端有没有新版本（那是 Pro / 云端能力）；不做回滚。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
- [术语表](./glossary.yaml)
- [快速开始](./QUICKSTART.md)
- [决策](./docs/DECISIONS.md)
