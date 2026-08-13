# Tag API 文档

**版本：** `0.4.0`  
**最低支持核心版本：** `>=0.4.4`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Tag`；hooks 与枚举从 [`contracts.py`](./contracts.py) 导入。  
**边界：** UI catalog/run 在 BFF；进度落盘 `TagRunProgress`（内部服务）。

---

## Tag

**描述：** 标签模块 Facade — discovery / execute / list

### __init__

`Tag(*, is_verbose: bool = False, dispatch_overrides: dict | None = None)`

- **状态：** `beta`
- **描述：** 构造时 `refresh()` 发现全部场景；`dispatch_overrides` 可含 `entity_limit` 等

### refresh

`tag.refresh() -> None`

- **状态：** `beta`
- **描述：** 重新 discovery（含未启用）

### list_ids / list_keys

`tag.list_ids(*, enabled_only: bool = True) -> list[str]`  
`tag.list_keys(*, enabled_only: bool = True) -> list[str]`

- **状态：** `beta`
- **描述：** 路径 id / key（或回退 id）列表

### find

`tag.find(key_or_id: str) -> DiscoveredTagInfo | None`

- **状态：** `beta`
- **描述：** 按路径 id 或 `meta.key` 查找；未命中缓存时再问 DiscoveryService

### is_valid_path

`Tag.is_valid_path(relative_path: str) -> bool`（staticmethod）

- **状态：** `beta`
- **描述：** 脚手架路径段机器可读校验；供 CLI 从模板新建等调用

### execute

`tag.execute(scenario_name=None, settings=None, *, tag_key=None, on_pipeline_progress=None, dry_run=False) -> dict | None`

- **状态：** `beta`
- **描述：** metadata ensure → pipeline → 落库
- **参数：**
  - `settings` + `tag_key`/`scenario_name`：内联 settings（仍需已 discovery 的 hooks）
  - `scenario_name`：按 key 或路径跑单个已启用场景
  - 皆空：跑全部已启用

**举例：**

```python
from core.modules.tag import Tag

Tag().execute(scenario_name="market_cap_tier")
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `TagHooks` / `TagContext` / `TagData` / `TagInfo` | userspace hook 契约 |
| `TagCalendarAsOfResult` | slice_based 横截面返回 |
| `TagUpdateMode` / `TagExecutionMode` | 更新与执行模式枚举 |

路由：`data.base` → per_entity（BE）/ global / non_time_series（主进程）。详见 [docs/DESIGN.md](./docs/DESIGN.md)。
