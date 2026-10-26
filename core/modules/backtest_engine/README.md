# Backtest Engine（`modules.backtest_engine`）

**模块：** `modules.backtest_engine` · **版本：** `0.2.0`

## 简介

把要跑的任务（比如策略模拟、批量算因子）拆成批次，按时间顺序一步步推进。支持两种推进方式：逐股跑（适合因子计算）和按时间切片跑（适合组合模拟），自动探测内存、避免爆内存。

## 适用场景

- Strategy 模块要模拟多策略组合、Tag 模块要批量算因子时调用
- 任务量大需要多进程并行，希望引擎自动决定怎么切批次

## 模块依赖

- `infra.db`：DuckDB 多进程连接的释放与恢复
- `infra.machine_capacity`：探测机器 CPU / 内存预算
- `infra.project_context`：定位 shared memory 文件与用户配置
- `modules.data_contract`：声明式数据契约
- `modules.data_manager`：底层数据读取

## 设计初衷

- **要解决的问题：** 回测调度是复杂的多进程问题，不能让 Strategy 和 Tag 各自实现一遍。
- **明确不做：** 不直接读业务数据（全部由调用方传入）；不做策略归因分析（那是 `strategy/engines/analyzer`）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [快速开始](./QUICKSTART.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [slice_based 算法](./docs/SLICE_BASED_ALGORITHM.md)
