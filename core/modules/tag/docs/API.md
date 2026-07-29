# Tag 模块 API 文档

**版本：** `0.4.1`

公开导出以 **`core.modules.tag`** / **`api.yaml`** 为准。配置字段以场景 **`settings.py`** 与 **`settings_example.py`** 为准。

---

## Tags 根路径

**`ProjectContext.path.get_tags_root()`**（通常为 **`userspace/extensions/tags`**）。

CLI 在 **`core/infra/cli`**：

```text
cli.py tag [--scenario PATH] [--list] [--dry-run] [--stock-limit N]
```

---

## 路由（`data.base`）

| base contract | 执行 |
|---------------|------|
| per_entity 时序 | BacktestEngine：`entity_based` / `slice_based` |
| global 时序 | `TagGlobalPipeline`（主进程；`execution.mode` 忽略） |
| non_time_series | 尚未实现 |

实体池：per_entity → `meta.list_data_key`；global → `__global__`。

---

## TagUpdateMode

| 成员 | 值 | 说明 |
|------|-----|------|
| `INCREMENTAL` | `incremental` | 增量更新 |
| `REFRESH` | `refresh` | 全量刷新 |

---

## Tag

`from core.modules.tag import Tag`

| 方法 | 说明 |
|------|------|
| `refresh()` | 重新 discovery |
| `list_ids()` / `list_keys()` | 列出已发现 tag |
| `find(key_or_id)` | 按路径或 meta.key 查找 |
| `execute(scenario_name=..., settings=..., dry_run=...)` | 执行；皆空则跑全部已启用 |

---

## TagHooks

userspace 场景目录的 **`tag.py`** 实现钩子（见 `contracts.TagHooks`）。

```python
from core.modules.tag import TagContext, TagHooks
```

- `calculate_tag(ctx)` — per_entity 的 entity_based；**global 主进程同样复用**
- `on_calendar_asof(ctx)` — 仅 per_entity 的 slice_based（可选）

旧 **`BaseTagWorker` / `tag_worker.py` / `TagManager`** 已移除。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [BOUNDARY_NOTES.md](BOUNDARY_NOTES.md)
- [DECISIONS.md](DECISIONS.md)
