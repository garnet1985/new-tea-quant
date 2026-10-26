# Trace（`infra.trace`）

**模块：** `infra.trace` · **版本：** `0.1.2`

## 简介

匿名 usage 上报。默认关闭（opt-in），用户同意才上报。去敏感化后静默发送，队列里发不出去就攒着，BFF 启动时后台 drain。**不**处理应用内软反馈（评分 + 文字反馈走 ntq_external）。

## 适用场景

- 安装完成、CLI 命令执行等关键事件，上报帮助维护者了解使用情况
- BFF / 长进程启动时后台发送积压的队列

## 模块依赖

- `infra.machine_capacity`：上报附带机器规格
- `infra.project_context`：路径与配置

## 设计初衷

- **要解决的问题：** 上报代码不能散落在各处，也不能默认就发——用户不同意时不能留下任何痕迹。
- **明确不做：** 不做强制上报；不做应用内反馈。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
- [术语表](./glossary.yaml)
- [快速开始](./QUICKSTART.md)
- [设计](./docs/DESIGN.md)
- [决策](./docs/DECISIONS.md)
