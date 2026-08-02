# Tag API 文档

**版本：** `0.5.0`  
**最低支持核心版本：** `>=0.4.4`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。

**公开约定：** 包根仅导出 `Tag`；hooks 与枚举从 [`contracts.py`](./contracts.py) 导入。  
**边界：** UI catalog/run 在 BFF；进度落盘 `TagRunProgress`。

---

## Tag

**描述：** 标签模块 Facade — discovery / execute / list

### execute

`Tag.execute(*, scenario_name=None, settings=None, tag_key=None, on_pipeline_progress=None, dry_run=False)`

- **类型：** `instance`
- **状态：** `beta`
- **描述：** metadata ensure → pipeline → 落库；皆空则跑全部已启用 tag

### refresh / list_ids / list_keys / find

- **类型：** `instance`
- **状态：** `beta`

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

路由：`data.base` → per_entity（BE）/ global / non_time_series（主进程推进器）。详见 [docs/DESIGN.md](./docs/DESIGN.md)。
