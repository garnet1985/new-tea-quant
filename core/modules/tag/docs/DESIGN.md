# Tag 设计说明

**版本：** `0.4.0`

---

## Scenario 与目录约定

- 根路径：`ProjectContext.path.get_tags_root()`（通常 `userspace/extensions/tags`）。
- 发现条件：子目录同时含 **`settings.py`** + **`tag.py`**（`TagHooks`）。
- **系统 id（tag_key / scenario 路径）** = 相对 tags 根的 POSIX 路径（如 `demo/market_cap_tier`）。
- `meta.key`：短名索引；CLI / `find` 可用路径或 key。DB scenario.name 用**路径**。
- 跳过 `_` 开头目录；路径段须 machine-readable。

---

## 执行模式

| `calculation.execution.mode` | 含义 |
|------------------------------|------|
| `entity_based` | 各实体按各自交易日推进；钩子 `calculate_tag(ctx)` |
| `slice_based` | 日历切片；钩子 `on_calendar_asof(ctx)`（当前须 recompute 或 `update_mode=refresh`） |

---

## 更新模式

| `update_mode` | 含义 |
|---------------|------|
| `incremental` | 从每实体 **`last_calculated_end`** 续算（不是 `max(as_of)`） |
| `refresh` | 对目标区间按重算语义清值后重算 |

`recompute=True`：运维开关，等价本次 refresh，并可重建 definition 元数据（**dry_run 时跳过清库**）。

水位文件：`userspace/.ntq/tag_calc_progress/`（`TagCalcProgressStore`）。

---

## Dry run

- settings：`calculation.is_dry_run`（默认 `False`）
- CLI：`--dry-run`
- 二者 OR：只计算、不写 `tag_value`、不更新 progress、不做 refresh/recompute 清库。

---

## 钩子面

userspace `tag.py` 继承 `TagHooks`：

- `calculate_tag(ctx)` — entity_based
- `on_calendar_asof(ctx)` — slice_based（可选）

旧 `BaseTagWorker` / `tag_worker.py` 生命周期钩子已移除。

---

## 数据与 as_of

- 数据声明在 `settings.data`（`base` / `required` / `min_required_records`），与 strategy 的 `data_key` 对齐。
- Job 内通过 `TagContext` / 注入数据按 as_of 可见；业务钩子不应偷看未来。

配置字段 SOT：`userspace/extensions/tags/settings_example.py`。
