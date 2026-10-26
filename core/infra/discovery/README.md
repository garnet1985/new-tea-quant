# Discovery（`infra.discovery`）

**模块：** `infra.discovery` · **版本：** `0.2.1`

## 简介

自动找文件和类。扫 userspace / core 下某个目录，把里面的 Provider、Handler、Strategy 等插件类找出来。代替各模块手写 importlib 扫描，统一走 `Discovery` 门面。

## 适用场景

- 启动时扫一遍 `userspace/extensions/data_source/` 下有哪些外部数据源
- 找所有继承了某个基类的插件实现

## 模块依赖

无硬依赖

## 设计初衷

- **要解决的问题：** 每个模块自己写文件扫描和类枚举是重复代码，集中一处。
- **明确不做：** 不定义业务基类；不做文件变更监视；不做跨进程缓存。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
