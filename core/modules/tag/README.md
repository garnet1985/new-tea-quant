# Tag

**模块：** `modules.tag` · **版本：** `0.5.0`

标签资产层：按 `data.base` 路由到 per_entity（BacktestEngine）或 global / non_time_series 主进程推进器。

## 文档

| 文档 | 内容 |
|------|------|
| [API.md](./API.md) | 公开 API |
| [QUICKSTART.md](./QUICKSTART.md) | 最短示例 |
| [docs/DESIGN.md](./docs/DESIGN.md) | 路由、更新模式、钩子 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 架构 |

## 公开 import

```python
from core.modules.tag import Tag
from core.modules.tag.contracts import TagHooks, TagContext
```

UI catalog/run：`core/bff/APIs/tag`。
