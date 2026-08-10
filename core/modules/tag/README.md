# Tag（`modules.tag`）

**版本：** `0.4.0` · 兼容 core `>=0.4.4`

标签资产层：按 `data.base` 路由到 per_entity（BacktestEngine）或 global / non_time_series 主进程推进器。对外门面为 `Tag`；hooks / 枚举见 `contracts`。

## 适用场景

- CLI / 工作台触发单个或全部已启用 tag 计算
- userspace 场景目录：`settings.py` + `tag.py`（`TagHooks`）

## 模块依赖

见 `module_info.yaml`（data_manager、data_contract、backtest_engine、project_context）。

## 设计初衷

- **要解决的问题：** 配置驱动的标签计算与落库，供策略复用。
- **明确不做：** 不在本模块另起平行于 BE 的调度（硬约束见 [docs/DESIGN.md](./docs/DESIGN.md) / [docs/notes/BOUNDARY_NOTES.md](./docs/notes/BOUNDARY_NOTES.md)）。

## 公开 import

```python
from core.modules.tag import Tag
from core.modules.tag.contracts import TagHooks, TagContext
```

UI catalog/run：`core/bff/APIs/tag`。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [边界笔记](./docs/notes/BOUNDARY_NOTES.md)
- [测试用例](./__test__/TEST_CASES.md)
