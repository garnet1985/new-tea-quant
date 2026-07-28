# Tag 模块 API 文档

**版本：** `0.4.0`

公开导出以 **`core.modules.tag`** / **`api.yaml`** 为准。配置字段以场景 **`settings.py`** 与 **`settings_example.py`** 为准。

---

## Tags 根路径

**`ProjectContext.path.get_tags_root()`**（通常为 **`userspace/extensions/tags`**）。

CLI 在 **`core/infra/cli`**：

```text
cli.py tag [--scenario PATH] [--list] [--dry-run] [--stock-limit N]
```

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

userspace 场景目录的 **`tag.py`** 实现钩子（见 `contracts.TagHooks`）。旧 **`BaseTagWorker` / `tag_worker.py` / `TagManager`** 已移除。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [BOUNDARY_NOTES.md](BOUNDARY_NOTES.md)
- [DECISIONS.md](DECISIONS.md)
