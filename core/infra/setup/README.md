# Setup（`infra.setup`）

**模块：** `infra.setup` · **版本：** `0.1.1`

## 简介

NTQ 的安装流程编排。首次启动时检测环境、创建目录、拷贝产物，装完就能跑。**不是** Python 的 setuptools——那是打包安装 Python 包的事，这个是装完之后让 NTQ 自己能跑的初始化流程。

## 适用场景

- 首次启动 NTQ 时，CLI 或 launcher 调这里完成安装
- 装 CLI 运行时或 UI 运行时等可选组件

## 模块依赖

- `infra.cmd_layout`：终端展示
- `infra.project_context`：路径定位
- `infra.trace`：上报安装事件
- `infra.utils`：通用工具

## 设计初衷

- **要解决的问题：** 安装流程在 CLI、BFF、独立安装器三处复用同一份编排，不各写一套。
- **明确不做：** 不做升级（那是 `infra.updater`）；不做业务配置迁移。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
- [术语表](./glossary.yaml)
- [快速开始](./QUICKSTART.md)
- [设计](./docs/DESIGN.md)
- [决策](./docs/DECISIONS.md)
