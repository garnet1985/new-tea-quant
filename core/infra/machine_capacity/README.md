# Machine Capacity（`infra.machine_capacity`）

**模块：** `infra.machine_capacity` · **版本：** `0.2.1`

**最低支持核心版本：** `>=0.5.0`

## 简介

探测本机硬件：CPU 核数、内存总大小、硬盘类型（SSD / HDD）。BacktestEngine 等调度器根据这些信息自动算能用多少 worker、内存预算多少。

## 适用场景

- 回测前需要自动决定开多少进程不爆内存
- 想知道当前机器的硬盘是 SSD 还是 HDD，影响 IO 密集型任务的调度策略

## 模块依赖

无硬依赖（运行需 Python `psutil`；缺失时用回退值）

## 设计初衷

- **要解决的问题：** 硬件探测从 BacktestEngine 里抽出来变成可复用的原语。
- **明确不做：** 不做进程池调度、不读配置文件里的手动设置。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [快速开始](./QUICKSTART.md)
- [决策](./docs/DECISIONS.md)
