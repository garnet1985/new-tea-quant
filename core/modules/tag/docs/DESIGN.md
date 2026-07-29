# Tag 设计说明

**版本：** `0.4.1`

---

## Scenario 与目录约定

- 根路径：`ProjectContext.path.get_tags_root()`（通常 `userspace/extensions/tags`）。
- 发现条件：子目录同时含 **`settings.py`** + **`tag.py`**（`TagHooks`）。
- **系统 id（tag_key / scenario 路径）** = 相对 tags 根的 POSIX 路径（如 `demo/market_cap_tier`）。
- `meta.key`：短名索引；CLI / `find` 可用路径或 key。DB scenario.name 用**路径**。
- 跳过 `_` 开头目录；路径段须 machine-readable。

---

## 路由：由 `data.base` 决定

| base（contract `scope` × `type`） | 调度 | `execution.mode` |
|-----------------------------------|------|------------------|
| **per_entity** + 时序 | BacktestEngine（多进程） | 必填：`entity_based` / `slice_based` |
| **global** + 时序 | Tag **轻量主进程推进器**（不走 BE） | 忽略；配置了则 warning |
| **non_time_series** | Tag 轻量主进程（不走 BE） | 忽略；配置了则 warning |

per_entity 的实体池：读 base 的 `meta.list_data_key`（如 `stock.list` / `index.list`）。  
global：哨兵实体（如 `__global__`）。详见 [DECISIONS.md](DECISIONS.md) 决策 1。

---

## 执行模式（仅 per_entity）

| `calculation.execution.mode` | 含义 |
|------------------------------|------|
| `entity_based` | 各实体按各自交易日推进；钩子 `calculate_tag(ctx)` |
| `slice_based` | 日历切片；钩子 `on_calendar_asof(ctx)`；`incremental` 同样走 progress 裁窗 |

---

## 更新模式

| `update_mode` | 含义 |
|---------------|------|
| `incremental` | 从每实体 **`last_calculated_end`** 续算（不是 `max(as_of)`）；写 progress |
| `refresh` | 对目标区间按重算语义清值后重算；**不写** progress（清库时一并清空） |

`recompute=True`：运维开关，等价本次 refresh，并可重建 definition 元数据（**dry_run 时跳过清库**）。

水位：``sys_tag_calc_progress``（``TagDataService.get_entity_calc_progress``）。

---

## Dry run

- settings：`calculation.is_dry_run`（默认 `False`）
- CLI：`--dry-run`
- 二者 OR：只计算、不写 `tag_value`、不更新 progress、不做 refresh/recompute 清库。

---

## 钩子面

userspace `tag.py` 继承 `TagHooks`：

- `calculate_tag(ctx)` — per_entity 的 entity_based；global 主进程推进也复用（哨兵 `entity_id`）
- `on_calendar_asof(ctx)` — per_entity 的 slice_based（可选）；返回 ``TagCalendarAsOfResult``

旧 `BaseTagWorker` / `tag_worker.py` 生命周期钩子已移除。

---

## 数据与 as_of

- 数据声明在 `settings.data`（`base` / `required` / `min_required_records`），与 strategy 的 `data_key` 对齐。
- 计算路径内通过 `TagContext` / 注入数据按 as_of 可见；业务钩子不应偷看未来。

配置字段 SOT：`userspace/extensions/tags/settings_example.py`。
