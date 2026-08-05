# Backtest Engine

**模块：** `modules.backtest_engine` · **版本：** `0.4.0`

回测调度 Facade：对 tag / strategy 提供 **probe → plan → execute → monitor** 流水线。数据装载由调用方经 `RunCallbacks` 注入，engine 不读业务 DB。

## 能力

- **调度任务**：探针决定 batch / slice 组装方式
- **推进回测**：`entity_based` 或 `slice_based` 两种模式
- **性能监控**：内存预算、进度、RunResult

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

## 文档

| 文档 | 内容 |
|------|------|
| [API.md](./API.md) | 公开 API 契约 |
| [QUICKSTART.md](./QUICKSTART.md) | 最短示例 |
| [glossary.yaml](./glossary.yaml) | 术语 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 架构与目录 |
| [docs/DESIGN.md](./docs/DESIGN.md) | 设计决策 |
| [docs/SLICE_BASED_ALGORITHM.md](./docs/SLICE_BASED_ALGORITHM.md) | **slice_based 算法 SOT（硬约束）** |
| [__performance__/README.md](./__performance__/README.md) | 调度空转性能基线（合成数据） |

## 公开 import

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks
```
