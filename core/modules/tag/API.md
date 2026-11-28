# Tag API 文档

**模块：** `modules.tag` · **版本：** `0.4.3`

**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Tag`；hooks 与枚举从 [`contracts.py`](./contracts.py) 导入。  
**边界：** `Tag.execute` 保持同步计算；UI/agent 异步壳（线程 / lease / 入队）在 BFF 或 agent。本 Facade 提供 discovery 与进度 IO，禁止跨模块 deep-import `core.services`。

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

### list_tag_infos / get_tag_info / resolve_path / resolve_folder

`Tag.list_tag_infos(*, enabled_only: bool = False) -> list[dict]`  
`Tag.get_tag_info(key_or_id: str, *, enabled_only: bool = False) -> dict | None`  
`Tag.resolve_path(key_or_id: str) -> str`  
`Tag.resolve_folder(key_or_id: str) -> Path`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** 不构造 `DataManager` 的 discovery 查询。`list_tag_infos` / `get_tag_info` 返回元数据字典（含 `folder` / `key` / `is_enabled` / `hooks_class_name` 等）；`resolve_*` 未命中抛 `FileNotFoundError`

### load_hooks_class

`Tag.load_hooks_class(tag_folder: Path, tag_key: str)`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** 加载 `tag.py` 中的 `TagHooks` 子类；失败返回 `None`

### fetch_catalog_page / fetch_visualization

`Tag.fetch_catalog_page(page, limit) -> (items, total, data_end)`  
`Tag.fetch_visualization(tag_key, entity_id=None) -> dict | None`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** UI 列表与可视化读模型（实现在 `services/catalog` / `services/visualization`）。BFF 只薄封装。

### list_definitions

`Tag.list_definitions(tag_ref: str) -> (rows, error | None)`（staticmethod）

- **状态：** `beta`
- **描述：** 某 tag 的 `tag_definitions` 行（`value/name/display_name/description`）。`tag_ref` 为 meta.key 或路径 id；CLI `list tag.<key>` 薄封装

### scaffold_from_template / apply_settings_patch / validate_artifact / interpret_execute_result

`Tag.scaffold_from_template(raw_path: str) -> dict`  
`Tag.apply_settings_patch(*, key, tag_py="", settings_py="") -> dict`  
`Tag.validate_artifact(*, key: str) -> dict`  
`Tag.interpret_execute_result(result) -> None`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** userspace 标签制品用例（实现在 `artifact_ops`）。CLI/agent 只薄封装。脚手架写 `extensions/tags/_template/empty_scenario`，`meta.key` 为目录叶名。`interpret_execute_result` 供异步壳共用成功判定。

### get_run_progress / seed_run_progress / mark_run_running / complete_run_progress / fail_run_progress / run_progress_callback

`Tag.get_run_progress(*, tag_key: str, job_id: str) -> dict | None`  
`Tag.seed_run_progress(tag_key, job_id) -> None`  
`Tag.mark_run_running(tag_key, job_id, *, label=...) -> None`  
`Tag.complete_run_progress(tag_key, job_id) -> None`  
`Tag.fail_run_progress(tag_key, job_id, message) -> None`  
`Tag.run_progress_callback(tag_key, job_id)`

- **类型：** `staticmethod`
- **状态：** `beta`
- **描述：** 异步打标的进度落盘 IO。编排（线程 / lease / 入队）由 BFF `TagRunLauncher` 或 agent `start_tag` 负责；计算仍调 `Tag.execute`

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
| `TagHooks` / `TagContext` / `TagData` / `TagInfo` | userspace hook 契约（含 `to_entity_list` / `calculate_tag` / `on_calendar_asof`） |
| `TagCalendarAsOfResult` | slice_based 横截面返回 |
| `TagUpdateMode` / `TagExecutionMode` | 更新与执行模式枚举 |

路由：`data.base` → per_entity（BE）/ global / non_time_series（主进程）。详见 [docs/DECISIONS.md](./docs/DECISIONS.md)。
